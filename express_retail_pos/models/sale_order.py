# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'express.approval.mixin']

    is_express_pos = fields.Boolean(
        string='Express POS Order', default=False, copy=False, index=True,
        help='Technical flag identifying orders created from the Express Retail Sales console.')
    is_within_7_days = fields.Boolean(
        string='Created Within Last 7 Days', copy=False, index=True,
        compute='_compute_is_within_7_days', store=True,
        help='Technical flag used by the Express POS Branch Manager visibility '
             'rule. Recomputed on write; also expired daily by a cron.')
    express_pos_note = fields.Char(string='Express POS Note', copy=False)
    express_pos_brand_id = fields.Many2one('express.pos.brand', string='Brand')
    express_pos_branch_id = fields.Many2one('express.pos.branch', string='Showroom/Branch')
    is_daily_closed = fields.Boolean(
        default=False, copy=False,
        help='Set when the day this order belongs to has been closed. Further edits require MD-level approval.')
    loyalty_card_id = fields.Many2one('express.loyalty.card', string='Loyalty Card', copy=False)
    loyalty_points_earned = fields.Float(copy=False, readonly=True)
    gift_card_ids = fields.Many2many('express.gift.card', string='Gift Cards Used', copy=False)

    # ------------------------------------------------------------------
    # 7-day visibility window (used by the Branch Manager ir.rule)
    # ------------------------------------------------------------------
    @api.depends('create_date')
    def _compute_is_within_7_days(self):
        cutoff = fields.Datetime.now() - relativedelta(days=7)
        for order in self:
            order.is_within_7_days = bool(order.create_date and order.create_date >= cutoff)

    @api.model
    def _cron_expire_7_day_window(self):
        cutoff = fields.Datetime.now() - relativedelta(days=7)
        expiring = self.search([
            ('is_within_7_days', '=', True),
            ('create_date', '<', cutoff),
        ])
        if expiring:
            expiring.write({'is_within_7_days': False})

    # ------------------------------------------------------------------
    # Approval guard: once an order is confirmed (or its day is closed),
    # edits to its lines and deletion must go through Manager -> GM -> MD.
    # ------------------------------------------------------------------
    def write(self, vals):
        if self.env.context.get('express_approval_bypass'):
            return super().write(vals)
        guarded_keys = {'order_line', 'partner_id', 'date_order', 'express_pos_branch_id'}
        for order in self:
            if (order.state in ('sale', 'done') or order.is_daily_closed) and guarded_keys.intersection(vals.keys()):
                is_backdated = 'date_order' in vals and order.is_daily_closed
                order._express_create_approval(
                    action_type='backdated' if is_backdated else 'edit',
                    old_values=order._express_snapshot(list(guarded_keys)),
                    new_values=vals,
                    reason=self.env.context.get('express_approval_reason'),
                    requires_md_direct=is_backdated,
                )
                raise UserError(_(
                    'This order (%s) is confirmed or its day is closed. Your change has been '
                    'submitted as an approval request and will be applied automatically once '
                    'Manager, GM and MD approval is complete.') % order.name)
        return super().write(vals)

    def unlink(self):
        if self.env.context.get('express_approval_bypass'):
            return super().unlink()
        for order in self:
            if order.state != 'draft':
                order._express_create_approval(
                    action_type='delete',
                    old_values=order._express_snapshot(['name', 'amount_total', 'state']),
                    new_values={},
                    reason=self.env.context.get('express_approval_reason'),
                )
                raise UserError(_(
                    'Order %s cannot be deleted directly. A deletion approval request has been '
                    'submitted.') % order.name)
        return super().unlink()

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    @api.model
    def _express_pos_get_param(self, key, default=False):
        return self.env['ir.config_parameter'].sudo().get_param(key, default)

    @api.model
    def _express_pos_get_walkin_partner(self):
        """Return (and lazily create) the generic Walk-in Customer partner."""
        param_id = self._express_pos_get_param('express_retail_pos.walkin_partner_id')
        partner = self.env['res.partner'].browse(int(param_id)) if param_id else self.env['res.partner']
        if not partner.exists():
            partner = self.env['res.partner'].search([('name', '=', 'Walk-in Customer')], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': 'Walk-in Customer',
                'company_type': 'person',
                'customer_rank': 1,
            })
        self.env['ir.config_parameter'].sudo().set_param('express_retail_pos.walkin_partner_id', partner.id)
        return partner

    @api.model
    def _express_pos_block_on_negative_stock(self):
        return self._express_pos_get_param('express_retail_pos.block_on_negative_stock', 'False') == 'True'

    # ------------------------------------------------------------------
    # Branch access (multi-branch security scoping)
    # ------------------------------------------------------------------
    @api.model
    def _express_pos_is_branch_unrestricted(self):
        """GM/MD (and technical admins) are not scoped to a specific branch."""
        return self.env.user.has_group('express_retail_pos.group_express_pos_gm')

    @api.model
    def express_pos_get_my_branches(self):
        """Branches the current user is allowed to sell from: all of them for
        GM/MD, otherwise only branches where they are staff or the manager.
        """
        Branch = self.env['express.pos.branch']
        if self._express_pos_is_branch_unrestricted():
            branches = Branch.search([('company_id', '=', self.env.company.id)])
        else:
            branches = Branch.search([
                ('company_id', '=', self.env.company.id),
                '|', ('user_ids', 'in', [self.env.uid]), ('manager_id', '=', self.env.uid),
            ])
        return [{
            'id': b.id, 'name': b.name, 'brand_id': b.brand_id.id,
            'brand_name': b.brand_id.name, 'color': b.color or '#1f5c3d',
        } for b in branches]

    @api.model
    def _express_pos_check_branch_access(self, branch_id):
        if not branch_id or self._express_pos_is_branch_unrestricted():
            return True
        branch = self.env['express.pos.branch'].browse(branch_id)
        if self.env.uid in (branch.manager_id.id, *branch.user_ids.ids):
            return True
        raise UserError(_('You are not assigned to the "%s" branch.') % branch.name)

    # ------------------------------------------------------------------
    # Session bootstrap
    # ------------------------------------------------------------------
    @api.model
    def express_pos_get_session_data(self):
        walkin = self._express_pos_get_walkin_partner()
        journals = self.env['account.journal'].search([
            ('type', 'in', ['cash', 'bank']),
            ('company_id', '=', self.env.company.id),
        ])
        # Cash first, then Bank, regardless of search/company order.
        type_order = {'cash': 0, 'bank': 1}
        journals = journals.sorted(key=lambda j: type_order.get(j.type, 2))
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        branches = self.express_pos_get_my_branches()
        categories = self.env['product.category'].search([], limit=40)
        return {
            'walkin_partner_id': walkin.id,
            'walkin_partner_name': walkin.name,
            'journals': [{'id': j.id, 'name': j.name, 'type': j.type} for j in journals],
            'warehouse_id': warehouse.id if warehouse else False,
            'currency_symbol': self.env.company.currency_id.symbol,
            'currency_position': self.env.company.currency_id.position,
            'block_on_negative_stock': self._express_pos_block_on_negative_stock(),
            'branches': branches,
            'categories': [{'id': c.id, 'name': c.name} for c in categories],
            'cashier_name': self.env.user.name,
            'company_name': self.env.company.name,
        }

    @api.model
    def express_pos_get_dashboard_kpis(self, branch_id=False):
        """Lightweight KPI ribbon for the console header. Deliberately runs
        through the normal (non-sudo) env so branch/7-day ir.rule scoping
        applies exactly as it does everywhere else in the module.
        """
        today_start = datetime.combine(fields.Date.context_today(self), time.min)
        domain = [
            ('is_express_pos', '=', True),
            ('state', 'in', ('sale', 'done')),
            ('date_order', '>=', fields.Datetime.to_string(today_start)),
        ]
        if branch_id:
            domain.append(('express_pos_branch_id', '=', branch_id))
        orders = self.search(domain)
        held = self.search([
                               ('is_express_pos', '=', True),
                               ('state', '=', 'draft'),
                               ('create_date', '>=', fields.Datetime.to_string(today_start)),
                           ] + ([('express_pos_branch_id', '=', branch_id)] if branch_id else []))
        return {
            'today_sales': sum(orders.mapped('amount_total')),
            'today_orders': len(orders),
            'held_orders': len(held),
            'avg_basket': (sum(orders.mapped('amount_total')) / len(orders)) if orders else 0.0,
        }

    # ------------------------------------------------------------------
    # Product search / barcode
    # ------------------------------------------------------------------
    @api.model
    def express_pos_search_products(self, query='', limit=60, category_id=False):
        domain = [('sale_ok', '=', True), ('type', 'in', ['product', 'consu'])]
        if query:
            domain += ['|', '|', ('name', 'ilike', query), ('default_code', 'ilike', query),
                       ('barcode', '=', query)]
        if category_id:
            domain.append(('categ_id', '=', category_id))
        products = self.env['product.product'].search(domain, limit=limit)
        return [{
            'id': p.id,
            'name': p.display_name,
            'list_price': p.list_price,
            'barcode': p.barcode or '',
            'default_code': p.default_code or '',
            'qty_available': p.qty_available,
            'uom_id': p.uom_id.id,
            'uom_name': p.uom_id.name,
            'image_128': bool(p.image_128),
        } for p in products]

    @api.model
    def express_pos_scan_barcode(self, barcode):
        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        if not product:
            return {'found': False, 'barcode': barcode}
        return {
            'found': True,
            'id': product.id,
            'name': product.display_name,
            'list_price': product.list_price,
            'qty_available': product.qty_available,
            'uom_id': product.uom_id.id,
            'uom_name': product.uom_id.name,
        }

    # ------------------------------------------------------------------
    # Draft order / cart lifecycle
    # ------------------------------------------------------------------
    @api.model
    def express_pos_get_or_create_draft(self, order_id=False, branch_id=False):
        order = self.browse(order_id) if order_id else self.env['sale.order']
        if order and order.exists() and order.state == 'draft':
            return order._express_pos_read()
        if branch_id:
            self._express_pos_check_branch_access(branch_id)
        else:
            my_branches = self.express_pos_get_my_branches()
            if len(my_branches) == 1:
                branch_id = my_branches[0]['id']
        walkin = self._express_pos_get_walkin_partner()
        vals = {
            'partner_id': walkin.id,
            'is_express_pos': True,
        }
        if branch_id:
            branch = self.env['express.pos.branch'].browse(branch_id)
            vals['express_pos_branch_id'] = branch_id
            vals['express_pos_brand_id'] = branch.brand_id.id
        order = self.create(vals)
        return order._express_pos_read()

    @api.model
    def express_pos_set_branch(self, order_id, branch_id):
        self._express_pos_check_branch_access(branch_id)
        order = self.browse(order_id)
        order.ensure_one()
        if order.state != 'draft':
            raise UserError(_('This order can no longer be modified.'))
        branch = self.env['express.pos.branch'].browse(branch_id)
        order.write({'express_pos_branch_id': branch_id, 'express_pos_brand_id': branch.brand_id.id})
        return order._express_pos_read()

    def _express_pos_read(self):
        self.ensure_one()
        return {
            'order_id': self.id,
            'name': self.name,
            'partner_id': self.partner_id.id,
            'partner_name': self.partner_id.name,
            'branch_id': self.express_pos_branch_id.id,
            'branch_name': self.express_pos_branch_id.name,
            'amount_total': self.amount_total,
            'amount_untaxed': self.amount_untaxed,
            'amount_tax': self.amount_tax,
            'lines': [{
                'id': l.id,
                'product_id': l.product_id.id,
                'name': l.product_id.display_name,
                'product_uom_qty': l.product_uom_qty,
                'price_unit': l.price_unit,
                'price_subtotal': l.price_subtotal,
                'discount': l.discount,
            } for l in self.order_line],
        }

    @api.model
    def express_pos_add_product(self, order_id, product_id, qty=1.0, mode='add'):
        order = self.browse(order_id)
        order.ensure_one()
        if order.state != 'draft':
            raise UserError(_('This order can no longer be modified.'))
        product = self.env['product.product'].browse(product_id)
        line = order.order_line.filtered(lambda l: l.product_id.id == product_id)
        if line:
            new_qty = (line.product_uom_qty + qty) if mode == 'add' else qty
            if float_compare(new_qty, 0.0, precision_digits=2) <= 0:
                line.unlink()
            else:
                line.product_uom_qty = new_qty
        else:
            order.write({'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'name': product.display_name,
            })]})
        stock_warning = False
        if product.type == 'product' and product.qty_available <= 0:
            stock_warning = True
            if order._express_pos_block_on_negative_stock():
                raise UserError(
                    _('Insufficient stock for "%s". Sale is blocked by configuration.') % product.display_name)
        result = order._express_pos_read()
        result['stock_warning'] = stock_warning
        return result

    @api.model
    def express_pos_remove_line(self, order_id, line_id):
        order = self.browse(order_id)
        order.ensure_one()
        if order.state != 'draft':
            raise UserError(_('This order can no longer be modified.'))
        line = self.env['sale.order.line'].browse(line_id)
        if line.order_id.id == order.id:
            line.unlink()
        return order._express_pos_read()

    @api.model
    def express_pos_set_customer(self, order_id, partner_id):
        order = self.browse(order_id)
        order.ensure_one()
        order.partner_id = partner_id
        return order._express_pos_read()

    @api.model
    def express_pos_quick_create_customer(self, name, mobile):
        name = (name or '').strip()
        mobile = (mobile or '').strip()
        if not mobile:
            raise UserError(_('Mobile number is required.'))
        if not mobile.isdigit() or len(mobile) != 11:
            raise UserError(_('Mobile number must be exactly 11 digits.'))
        # Reuse the existing contact for this mobile instead of creating a duplicate
        existing = self.env['res.partner'].search([('mobile', '=', mobile)], limit=1)
        if existing:
            return {'id': existing.id, 'name': existing.name}
        partner = self.env['res.partner'].create({
            'name': name or mobile,
            'mobile': mobile,
            'customer_rank': 1,
        })
        return {'id': partner.id, 'name': partner.name}

    # ------------------------------------------------------------------
    # Hold / Park
    # ------------------------------------------------------------------
    def action_express_hold(self):
        self.ensure_one()
        self.is_express_pos = True
        return {'order_id': self.id}

    @api.model
    def express_pos_get_parked_orders(self):
        today_start = datetime.combine(fields.Date.context_today(self), time.min)
        orders = self.search([
            ('is_express_pos', '=', True),
            ('state', '=', 'draft'),
            ('create_date', '>=', fields.Datetime.to_string(today_start)),
        ], order='create_date desc')
        return [{
            'id': o.id,
            'name': o.name,
            'partner_name': o.partner_id.name,
            'amount_total': o.amount_total,
            'line_count': len(o.order_line),
        } for o in orders]

    # ------------------------------------------------------------------
    # Stock validation helper (immediate transfer is context-driven in 17.0;
    # the stock.immediate.transfer wizard model from older versions no
    # longer exists, so we pass skip_immediate/skip_backorder instead and
    # only fall back to the backorder wizard if it still returns an action)
    # ------------------------------------------------------------------
    def _express_pos_validate_pickings(self, pickings):
        StockBackorder = self.env['stock.backorder.confirmation']
        for picking in pickings:
            if picking.state == 'done':
                continue
            if picking.state not in ('assigned',):
                picking.action_assign()
            res = picking.with_context(
                skip_immediate=True, skip_backorder=True
            ).button_validate()
            if isinstance(res, dict) and res.get('res_model'):
                model_name = res['res_model']
                wizard_ctx = res.get('context', {})
                if model_name == 'stock.backorder.confirmation':
                    wizard = StockBackorder.with_context(wizard_ctx).create({
                        'pick_ids': [(6, 0, wizard_ctx.get('default_pick_ids', picking.ids))],
                    })
                    wizard.process_cancel_backorder()
        return True

    # ------------------------------------------------------------------
    # One-Click Checkout Automation
    # ------------------------------------------------------------------
    def action_express_pos_checkout(self, payment_lines=None, gift_card_lines=None, allow_due=False):
        """payment_lines: list of {'journal_id': int, 'amount': float}
        gift_card_lines: optional list of {'code': str, 'amount': float} to redeem
        against active gift cards, covering part of the amount due.
        allow_due: cashier explicitly chose "Sell on Credit / Due" - the sale is
        completed even if entered payments fall short of the amount due, leaving
        the difference as an open receivable. Walk-in customers are blocked since
        the balance needs a real, trackable contact.
        """
        self.ensure_one()
        payment_lines = payment_lines or []
        gift_card_lines = gift_card_lines or []
        if not self.order_line:
            raise UserError(_('Cannot checkout an empty cart.'))
        if allow_due:
            walkin = self._express_pos_get_walkin_partner()
            if self.partner_id.id == walkin.id:
                raise UserError(_('Select a real customer before selling on credit/due - the '
                                  'Walk-in Customer cannot carry a balance.'))

        # Redeem gift cards first (validated but applied after invoice exists)
        gift_cards_to_redeem = []
        gift_total = 0.0
        for gcl in gift_card_lines:
            amount = gcl.get('amount', 0.0)
            if amount <= 0:
                continue
            card = self.env['express.gift.card'].search([('code', '=', gcl.get('code'))], limit=1)
            if not card:
                raise UserError(_('Gift card "%s" not found.') % gcl.get('code'))
            if amount > card.balance:
                raise UserError(_('Gift card %s has insufficient balance.') % card.code)
            gift_cards_to_redeem.append((card, amount))
            gift_total += amount

        total_payment = sum(pl.get('amount', 0.0) for pl in payment_lines) + gift_total
        if not allow_due and float_compare(total_payment, self.amount_total, precision_digits=2) < 0:
            raise UserError(_('Payment total (%.2f) is less than the amount due (%.2f).') % (
                total_payment, self.amount_total))

        # 1. Confirm order
        if self.state in ('draft', 'sent'):
            self.action_confirm()

        # 2. Deliver stock
        pickings = self.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        self._express_pos_validate_pickings(pickings)

        # 3. Create invoice
        invoice_ids = self._create_invoices(final=True)
        invoices = self.env['account.move'].browse(invoice_ids.ids if hasattr(invoice_ids, 'ids') else invoice_ids)

        # 4. Post invoice
        invoices.filtered(lambda m: m.state == 'draft').action_post()

        # 5. Register split payments
        for pl in payment_lines:
            amount = pl.get('amount', 0.0)
            if float_is_zero(amount, precision_digits=2):
                continue
            wizard = self.env['account.payment.register'].with_context(
                active_model='account.move', active_ids=invoices.ids
            ).create({
                'journal_id': pl['journal_id'],
                'amount': amount,
                'payment_date': fields.Date.context_today(self),
            })
            wizard.action_create_payments()

        # 5b. Register gift-card portion as payment against a dedicated gift-card journal
        # if configured, then decrement each card's balance.
        if gift_cards_to_redeem:
            gc_journal_id = self._express_pos_get_param('express_retail_pos.gift_card_journal_id')
            for card, amount in gift_cards_to_redeem:
                card.redeem(amount)
                self.gift_card_ids = [(4, card.id)]
                if gc_journal_id:
                    wizard = self.env['account.payment.register'].with_context(
                        active_model='account.move', active_ids=invoices.ids
                    ).create({
                        'journal_id': int(gc_journal_id),
                        'amount': amount,
                        'payment_date': fields.Date.context_today(self),
                    })
                    wizard.action_create_payments()

        # 6. Award loyalty points
        if self.loyalty_card_id:
            self.loyalty_points_earned = self.loyalty_card_id.add_points(self.amount_total) or 0.0

        # 7. Record what was actually tendered for the printed receipt (Receive /
        # Exchange / Mode of Payment) - captured here, at the moment of checkout,
        # rather than reverse-engineered later from invoice reconciliation.
        method_names = [pl['journal_id'] and self.env['account.journal'].browse(
            pl['journal_id']).name for pl in payment_lines if not float_is_zero(
            pl.get('amount', 0.0), precision_digits=2)]
        if gift_total:
            method_names.append(_('Gift Card'))
        method_names = [m for m in method_names if m]
        self.write({
            'express_pos_checkout_amount_paid': total_payment,
            'express_pos_checkout_payment_methods': ', '.join(dict.fromkeys(method_names)) or (
                _('Due / Credit') if allow_due and total_payment < self.amount_total else _('Cash')),
        })

        return {
            'order_id': self.id,
            'invoice_ids': invoices.ids,
            'invoice_names': invoices.mapped('name'),
            'amount_total': self.amount_total,
            'amount_due_remaining': max(0.0, self.amount_total - total_payment),
            'loyalty_points_earned': self.loyalty_points_earned,
        }

    @api.model
    def express_pos_checkout(self, order_id, payment_lines, gift_card_lines=None, allow_due=False):
        order = self.browse(order_id)
        return order.action_express_pos_checkout(payment_lines, gift_card_lines, allow_due=allow_due)

    # ------------------------------------------------------------------
    # Duplicate invoice / receipt reprint
    # ------------------------------------------------------------------
    def action_view_express_approvals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approval Requests'),
            'res_model': 'express.approval.request',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', 'sale.order'), ('res_id', '=', self.id)],
        }

    def action_express_print_duplicate_receipt(self):
        """Reprint the thermal receipt clearly marked as a duplicate copy."""
        self.ensure_one()
        return self.env.ref('express_retail_pos.action_report_express_pos_receipt').with_context(
            is_duplicate=True
        ).report_action(self)

    # ------------------------------------------------------------------
    # Loyalty / Offer engine
    # ------------------------------------------------------------------
    @api.model
    def express_pos_apply_offers(self, order_id):
        """Evaluate active loyalty/discount rules (style number, showroom, total
        bill tier, and Buy-X-Get-Y) against the current cart and apply them.
        Only the single best-matching style/showroom discount is applied per line
        to avoid uncontrolled stacking; BOGO free quantity is blended into the
        line discount; total-bill tiers are added as a separate discount line.
        """
        order = self.browse(order_id)
        order.ensure_one()
        Rule = self.env['express.loyalty.rule']
        domain = [('active', '=', True)]
        if order.express_pos_brand_id:
            domain += ['|', ('brand_id', '=', False), ('brand_id', '=', order.express_pos_brand_id.id)]
        if order.express_pos_branch_id:
            domain += ['|', ('branch_id', '=', False), ('branch_id', '=', order.express_pos_branch_id.id)]
        rules = Rule.search(domain)
        rules = rules.filtered(lambda r: r._is_active_today())

        style_rules = rules.filtered(lambda r: r.rule_type == 'style')
        showroom_rules = rules.filtered(lambda r: r.rule_type == 'showroom')
        bogo_rules = rules.filtered(lambda r: r.rule_type == 'bogo')
        total_bill_rules = rules.filtered(lambda r: r.rule_type == 'total_bill')

        for line in order.order_line:
            if line.display_type:
                continue
            best_discount = 0.0
            style_number = getattr(line.product_id.product_tmpl_id, 'style_number', False)
            for r in style_rules:
                if r.style_number and style_number and r.style_number == style_number:
                    best_discount = max(best_discount, r.discount_percent)
            for r in showroom_rules:
                if r.branch_id and order.express_pos_branch_id and r.branch_id == order.express_pos_branch_id:
                    best_discount = max(best_discount, r.discount_percent)

            free_ratio = 0.0
            for r in bogo_rules:
                if r.bogo_product_id and r.bogo_product_id != line.product_id:
                    continue
                cycle = r.buy_qty + r.get_qty
                if cycle <= 0:
                    continue
                cycles = int(line.product_uom_qty // cycle)
                if cycles > 0:
                    free_units = cycles * r.get_qty
                    ratio = min(1.0, (free_units * (r.get_discount_percent / 100.0)) / line.product_uom_qty)
                    free_ratio = max(free_ratio, ratio)

            blended = 1 - (1 - best_discount / 100.0) * (1 - free_ratio)
            if blended > 0:
                line.discount = round(blended * 100.0, 2)

        # Total bill-wise tier: applied as a single discount line using a generic
        # "Loyalty / Bill Discount" service product so it doesn't distort per-line data.
        applicable_tier = False
        for r in total_bill_rules:
            if order.amount_untaxed >= r.min_amount and (
                    not applicable_tier or r.min_amount > applicable_tier.min_amount):
                applicable_tier = r
        order.order_line.filtered(lambda l: l.express_pos_is_offer_line).unlink()
        if applicable_tier:
            discount_amount = -1 * order.amount_untaxed * (applicable_tier.discount_percent / 100.0)
            discount_product = order._express_pos_get_offer_product()
            order.write({'order_line': [(0, 0, {
                'product_id': discount_product.id,
                'name': _('Loyalty Discount (%s%%)') % applicable_tier.discount_percent,
                'product_uom_qty': 1,
                'price_unit': discount_amount,
                'express_pos_is_offer_line': True,
            })]})

        return order._express_pos_read()

    @api.model
    def _express_pos_get_offer_product(self):
        product = self.env['product.product'].search([('default_code', '=', 'EXPRESS_LOYALTY_DISCOUNT')], limit=1)
        if not product:
            product = self.env['product.product'].create({
                'name': 'Loyalty / Bill Discount',
                'default_code': 'EXPRESS_LOYALTY_DISCOUNT',
                'type': 'service',
                'sale_ok': True,
                'purchase_ok': False,
                'invoice_policy': 'order',
                'list_price': 0.0,
            })
        return product

    @api.model
    def express_pos_set_loyalty_card(self, order_id, card_code):
        order = self.browse(order_id)
        card = self.env['express.loyalty.card'].search([('card_code', '=', card_code)], limit=1)
        if not card:
            raise UserError(_('No loyalty card found for code "%s".') % card_code)
        order.loyalty_card_id = card.id
        return {'card_id': card.id, 'points': card.points, 'mobile_verified': card.mobile_verified}

    @api.model
    def express_pos_get_receipt_data(self, order_id):
        order = self.browse(order_id)
        order.ensure_one()
        invoices = order.invoice_ids.filtered(lambda m: m.state == 'posted')
        return {
            'company_name': self.env.company.name,
            'order_name': order.name,
            'invoice_name': invoices[:1].name if invoices else '',
            'partner_name': order.partner_id.name,
            'date': fields.Datetime.to_string(fields.Datetime.now()),
            'lines': [{
                'name': l.product_id.display_name,
                'qty': l.product_uom_qty,
                'price_unit': l.price_unit,
                'subtotal': l.price_subtotal,
            } for l in order.order_line],
            'amount_untaxed': order.amount_untaxed,
            'amount_tax': order.amount_tax,
            'amount_total': order.amount_total,
        }

    # ------------------------------------------------------------------
    # Express Return / Exchange
    # ------------------------------------------------------------------
    @api.model
    def express_pos_search_source_orders(self, query):
        domain = [('state', '=', 'sale')]
        if query:
            domain += ['|', ('name', 'ilike', query), ('partner_id.name', 'ilike', query)]
        orders = self.search(domain, limit=20, order='create_date desc')
        return [{'id': o.id, 'name': o.name, 'partner_name': o.partner_id.name,
                 'amount_total': o.amount_total} for o in orders]

    @api.model
    def express_pos_get_order_lines_for_return(self, order_id):
        order = self.browse(order_id)
        order.ensure_one()
        return {
            'order_id': order.id,
            'name': order.name,
            'lines': [{
                'line_id': l.id,
                'product_id': l.product_id.id,
                'name': l.product_id.display_name,
                'qty_ordered': l.product_uom_qty,
                'qty_delivered': l.qty_delivered,
                'price_unit': l.price_unit,
            } for l in order.order_line if l.product_id.type in ('product', 'consu')],
        }

    def action_express_return(self, return_lines):
        """return_lines: list of {'line_id': int, 'qty': float}
        Sales returns/refunds are a controlled action: unless called with the
        internal approval-bypass context (i.e. by the approval engine once fully
        approved), this submits an approval request instead of executing directly.
        """
        self.ensure_one()
        return_lines = [rl for rl in (return_lines or []) if rl.get('qty', 0) > 0]
        if not return_lines:
            raise UserError(_('Select at least one product/quantity to return.'))

        if not self.env.context.get('express_approval_bypass'):
            self._express_create_approval(
                action_type='sales_return',
                old_values=self._express_snapshot(['name', 'amount_total']),
                new_values={'return_lines': return_lines},
                reason=self.env.context.get('express_approval_reason'),
            )
            return {
                'source_order': self.name,
                'return_picking_ids': [],
                'credit_note_ids': [],
                'credit_note_names': [],
                'pending_approval': True,
            }
        return self._do_express_return(return_lines)

    def _do_express_return(self, return_lines):
        """Creates a reverse stock picking and a credit note limited to the selected
        products/quantities, then registers an outbound refund payment.
        """
        self.ensure_one()
        qty_by_product = {}
        for rl in return_lines:
            line = self.env['sale.order.line'].browse(rl['line_id'])
            if line.order_id.id != self.id:
                continue
            qty_by_product[line.product_id.id] = qty_by_product.get(line.product_id.id, 0.0) + rl['qty']

        # --- Stock reverse ---
        done_pickings = self.picking_ids.filtered(lambda p: p.state == 'done')
        new_return_pickings = self.env['stock.picking']
        for picking in done_pickings:
            return_wizard = self.env['stock.return.picking'].with_context(
                active_id=picking.id, active_model='stock.picking'
            ).create({})
            return_wizard._onchange_picking_id() if hasattr(return_wizard, '_onchange_picking_id') else None
            for return_line in return_wizard.product_return_moves:
                pid = return_line.product_id.id
                if pid in qty_by_product:
                    return_line.quantity = min(qty_by_product[pid], return_line.quantity)
                else:
                    return_line.quantity = 0.0
            action = return_wizard.create_returns()
            if action and action.get('res_id'):
                new_return_pickings |= self.env['stock.picking'].browse(action['res_id'])
        self._express_pos_validate_pickings(new_return_pickings)

        # --- Credit note ---
        invoices = self.invoice_ids.filtered(lambda m: m.state == 'posted' and m.move_type == 'out_invoice')
        credit_notes = self.env['account.move']
        if invoices:
            reversal = self.env['account.move.reversal'].with_context(
                active_model='account.move', active_ids=invoices.ids
            ).create({
                'reason': _('Express POS Return'),
                'journal_id': invoices[:1].journal_id.id,
            })
            result = reversal.reverse_moves()
            if isinstance(result, dict) and result.get('res_id'):
                credit_notes |= self.env['account.move'].browse(result['res_id'])
            elif isinstance(result, dict) and result.get('domain'):
                credit_notes |= self.env['account.move'].search(result['domain'])

            # Limit credit note lines to returned products/qty only
            for cn in credit_notes:
                for cline in cn.invoice_line_ids:
                    pid = cline.product_id.id
                    if pid in qty_by_product:
                        cline.quantity = qty_by_product[pid]
                    else:
                        cn.invoice_line_ids -= cline
                cn.action_post()

        # --- Refund payment (outbound) ---
        refund_payments = self.env['account.payment']
        if credit_notes:
            wizard = self.env['account.payment.register'].with_context(
                active_model='account.move', active_ids=credit_notes.ids
            ).create({
                'payment_date': fields.Date.context_today(self),
            })
            payment_result = wizard.action_create_payments()
            if isinstance(payment_result, dict) and payment_result.get('res_id'):
                refund_payments |= self.env['account.payment'].browse(payment_result['res_id'])

        return {
            'source_order': self.name,
            'return_picking_ids': new_return_pickings.ids,
            'credit_note_ids': credit_notes.ids,
            'credit_note_names': credit_notes.mapped('name'),
        }

    @api.model
    def express_pos_process_return(self, order_id, return_lines):
        order = self.browse(order_id)
        return order.action_express_return(return_lines)
