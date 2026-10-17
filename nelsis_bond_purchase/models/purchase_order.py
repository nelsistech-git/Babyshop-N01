# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    bond_purchase_type = fields.Selection(
        [('local', 'Local / Standard'),
         ('import_bonded', 'Import - Bonded'),
         ('import_non_bonded', 'Import - Non-Bonded (duty paid)')],
        string='Bond Purchase Type', default='local', required=True, tracking=True, index=True)
    lc_id = fields.Many2one(
        'nelsis.lc', string='Letter of Credit', copy=False, tracking=True, index=True, ondelete='restrict',
        domain="[('company_id', '=', company_id), ('state', 'not in', ['cancelled', 'closed'])]")
    bond_entitlement_id = fields.Many2one(
        'bond.warehouse.entitlement', string='Bond Entitlement', copy=False, tracking=True, index=True,
        ondelete='restrict', domain="[('state', '=', 'active'), ('company_id', '=', company_id)]")
    commercial_file_id = fields.Many2one(
        'nelsis.commercial.file', string='Commercial File', copy=False, tracking=True, index=True,
        ondelete='restrict', domain="[('company_id', '=', company_id)]")
    bond_consignment_ids = fields.One2many('bond.inventory.consignment', 'purchase_order_id', string='Bond Consignments')
    bond_receipt_ids = fields.One2many('bond.inventory.receipt', 'purchase_order_id', string='Bond Receipts')
    bond_consignment_count = fields.Integer(compute='_compute_bond_counts')
    bond_receipt_count = fields.Integer(compute='_compute_bond_counts')
    bond_has_uncovered_qty = fields.Boolean(compute='_compute_bond_counts')
    bond_received_percent = fields.Float('Received %', compute='_compute_bond_received_percent')
    lc_available_amount = fields.Monetary('LC Left After This Order', currency_field='currency_id',
                                          compute='_compute_lc_available')

    # ------------------------------------------------------------------ computes
    @api.depends('bond_consignment_ids', 'bond_receipt_ids', 'state', 'bond_purchase_type',
                 'order_line.bond_uncovered_qty')
    def _compute_bond_counts(self):
        real = [i for i in self.ids if isinstance(i, int)]
        cons, recs = {}, {}
        if real:
            for po, n in self.env['bond.inventory.consignment'].sudo()._read_group(
                    [('purchase_order_id', 'in', real), ('state', '!=', 'cancelled')],
                    ['purchase_order_id'], ['__count']):
                cons[po.id] = n
            for po, n in self.env['bond.inventory.receipt'].sudo()._read_group(
                    [('purchase_order_id', 'in', real)], ['purchase_order_id'], ['__count']):
                recs[po.id] = n
        for po in self:
            po.bond_consignment_count = cons.get(po.id, 0)
            po.bond_receipt_count = recs.get(po.id, 0)
            po.bond_has_uncovered_qty = (
                po.bond_purchase_type == 'import_bonded' and po.state in ('purchase', 'done')
                and any(l.bond_uncovered_qty > 0 for l in po.order_line if not l.display_type and l.product_id))

    @api.depends('order_line.qty_received', 'order_line.product_qty')
    def _compute_bond_received_percent(self):
        for po in self:
            lines = po.order_line.filtered(lambda l: not l.display_type and l.product_id and l.product_qty)
            ordered = sum(lines.mapped('product_qty'))
            received = sum(min(l.qty_received, l.product_qty) for l in lines)
            po.bond_received_percent = (received / ordered * 100.0) if ordered else 0.0

    @api.depends('lc_id', 'lc_id.current_amount', 'lc_id.tolerance_percent', 'amount_total')
    def _compute_lc_available(self):
        for po in self:
            lc = po.lc_id
            if lc and isinstance(po.id, int):
                limit = lc.current_amount * (1 + lc.tolerance_percent / 100.0)
                po.lc_available_amount = limit - lc._bond_po_committed(exclude=po) - po.amount_total
            else:
                po.lc_available_amount = 0.0

    @api.depends('order_line.qty_received', 'order_line.product_qty', 'bond_purchase_type', 'state')
    def _compute_receipt_status(self):
        # Standard status only looks at transfer states; a bond receipt is one transfer per delivery,
        # so for bonded orders the status follows the received quantities instead.
        super()._compute_receipt_status()
        for po in self.filtered(lambda p: p.bond_purchase_type == 'import_bonded'):
            lines = po._bond_product_lines()
            if po.state not in ('purchase', 'done') or not lines:
                po.receipt_status = False
            elif all(float_compare(l.qty_received, l.product_qty, precision_rounding=l.product_uom.rounding) >= 0
                     for l in lines):
                po.receipt_status = 'full'
            elif any(l.qty_received > 0 for l in lines):
                po.receipt_status = 'partial'
            else:
                po.receipt_status = 'pending'

    # ------------------------------------------------------------------ constraints
    @api.constrains('lc_id', 'partner_id', 'currency_id', 'company_id', 'commercial_file_id', 'bond_entitlement_id')
    def _check_bond_links(self):
        for po in self:
            lc = po.lc_id.sudo()
            if lc:
                if lc.company_id != po.company_id:
                    raise ValidationError(_('LC %s belongs to another company.', lc.display_name))
                if lc.state == 'cancelled':
                    raise ValidationError(_('LC %s is cancelled.', lc.display_name))
                if lc.partner_id.commercial_partner_id != po.partner_id.commercial_partner_id:
                    raise ValidationError(_('LC %(lc)s is issued for %(a)s, but the order supplier is %(b)s.',
                                            lc=lc.display_name, a=lc.partner_id.display_name,
                                            b=po.partner_id.display_name))
                if lc.currency_id != po.currency_id:
                    raise ValidationError(_('LC %(lc)s is in %(a)s but the order is in %(b)s. '
                                            'No currency conversion is done between them.',
                                            lc=lc.display_name, a=lc.currency_id.name, b=po.currency_id.name))
            file = po.commercial_file_id.sudo()
            if file:
                if file.company_id != po.company_id:
                    raise ValidationError(_('Commercial file %s belongs to another company.', file.display_name))
                file_lc = file.lc_ref
                if lc and file_lc and file_lc._name == 'nelsis.lc' and file_lc != lc:
                    raise ValidationError(_('Commercial file %(f)s is linked to LC %(a)s, the order to LC %(b)s.',
                                            f=file.display_name, a=file_lc.display_name, b=lc.display_name))
            ent = po.bond_entitlement_id.sudo()
            if ent and ent.company_id != po.company_id:
                raise ValidationError(_('Entitlement %s belongs to another company.', ent.display_name))

    # ------------------------------------------------------------------ write guard
    def write(self, vals):
        if 'bond_purchase_type' in vals:
            for po in self:
                if po.bond_purchase_type != vals['bond_purchase_type'] and po.state in ('purchase', 'done'):
                    raise UserError(_('The purchase type of a confirmed order cannot be changed (%s).', po.name))
        return super().write(vals)

    # ------------------------------------------------------------------ confirmation checks
    def _bond_product_lines(self):
        return self.order_line.filtered(lambda l: not l.display_type and l.product_id)

    def _bond_collect_issues(self):
        """Return (blocking, warnings) message lists for this order."""
        self.ensure_one()
        block, warn = [], []
        company = self.company_id
        lc = self.lc_id.sudo()
        if self.bond_purchase_type == 'import_bonded':
            lines = self._bond_product_lines()
            if not lines:
                block.append(_('A bonded purchase needs at least one product line.'))
            if company.bond_po_require_lc and not lc:
                block.append(_('A bonded purchase must be linked to a Letter of Credit.'))
            seen = {}
            for line in lines:
                tmpl = line.product_id.product_tmpl_id
                name = line.product_id.display_name
                if not tmpl.bond_eligible:
                    block.append(_('%s is not bond-eligible (no approved classification).', name))
                elif not tmpl.bond_hs_code:
                    block.append(_('%s has no HS code.', name))
                if line.product_id.tracking not in ('lot', 'serial'):
                    block.append(_('%s must be lot or serial tracked.', name))
                key = (line.product_id.id, line.product_uom.id)
                if key in seen:
                    block.append(_('%s appears on more than one line with the same unit. '
                                   'Merge the lines so receipts can be matched to the order.', name))
                seen[key] = True
            if company.bond_po_entitlement_policy != 'off':
                msgs = self._bond_entitlement_issues()
                (block if company.bond_po_entitlement_policy == 'block' else warn).extend(msgs)
        if lc:
            if lc.state in ('closed', 'hold'):
                block.append(_('LC %(lc)s is %(s)s.', lc=lc.display_name, s=lc.state))
            if company.bond_po_lc_limit_policy != 'off' and lc.current_amount:
                limit = lc.current_amount * (1 + lc.tolerance_percent / 100.0)
                total = lc._bond_po_committed(exclude=self) + self.amount_total
                if total > limit + 0.005:
                    msg = _('Orders on LC %(lc)s would total %(t).2f, above the LC limit %(l).2f '
                            '(amount plus tolerance).', lc=lc.display_name, t=total, l=limit)
                    (block if company.bond_po_lc_limit_policy == 'block' else warn).append(msg)
        return block, warn

    def _bond_entitlement_issues(self):
        self.ensure_one()
        issues = []
        today = fields.Date.context_today(self)
        Ent = self.env['bond.warehouse.entitlement'].sudo()
        products = self._bond_product_lines().mapped('product_id')
        for product in products:
            lines = self._bond_product_lines().filtered(lambda l: l.product_id == product)
            if self.bond_entitlement_id:
                ents = self.bond_entitlement_id.sudo().filtered(lambda e: not e.product_id or e.product_id == product)
            else:
                ents = Ent.search([('state', '=', 'active'), ('company_id', '=', self.company_id.id),
                                   ('product_id', '=', product.id)])
            ents = ents.filtered(lambda e: e.state == 'active' and (not e.effective_from or e.effective_from <= today)
                                 and (not e.effective_to or e.effective_to >= today))
            if not ents:
                issues.append(_('No active entitlement covers %s.', product.display_name))
                continue
            covered = False
            for ent in ents:
                if ent.exception_authorized:
                    covered = True
                    break
                if ent.basis == 'value':
                    need = sum(l.currency_id._convert(l.price_subtotal, ent.currency_id, self.company_id,
                                                      self.date_order or today) for l in lines)
                else:
                    need = 0.0
                    for l in lines:
                        if l.product_uom.category_id == ent.uom_id.category_id:
                            need += l.product_uom._compute_quantity(l.product_qty, ent.uom_id)
                if float_compare(need, ent.available_amount, precision_digits=4) <= 0:
                    covered = True
                    break
            if not covered:
                issues.append(_('The order quantity / value of %s is above the available entitlement.',
                                product.display_name))
        return issues

    def _bond_check_before_confirm(self, notify=False):
        for po in self:
            block, warn = po._bond_collect_issues()
            if block:
                raise UserError(_('Purchase order %(po)s cannot be confirmed:\n- %(m)s',
                                  po=po.name, m='\n- '.join(block)))
            if notify and warn:
                po.message_post(body=_('Bond purchase warnings:<br/>%s', '<br/>'.join(warn)))

    def button_confirm(self):
        self._bond_check_before_confirm()
        return super().button_confirm()

    def button_approve(self, force=False):
        self._bond_check_before_confirm(notify=True)
        res = super().button_approve(force=force)
        self.filtered(lambda p: p.state in ('purchase', 'done'))._bond_after_approve()
        return res

    def _bond_after_approve(self):
        for po in self:
            lc = po.lc_id.sudo()
            if lc:
                lc._log(_('Purchase order %(po)s confirmed (%(a).2f %(c)s).',
                          po=po.name, a=po.amount_total, c=po.currency_id.name))
            if po.bond_purchase_type == 'import_bonded':
                po.message_post(body=_('Bonded import: no standard receipt is created. Create a bond consignment '
                                       'and receive the goods through a bond receipt.'))
            if po.commercial_file_id or lc:
                po._bond_sync_links()

    def _create_picking(self):
        bonded = self.filtered(lambda p: p.bond_purchase_type == 'import_bonded')
        return super(PurchaseOrder, self - bonded)._create_picking()

    def button_cancel(self):
        for po in self:
            for cons in po.sudo().bond_consignment_ids.filtered(lambda c: c.state in ('draft', 'open')):
                cons.action_cancel()
        return super().button_cancel()

    # ------------------------------------------------------------------ creation helpers
    def action_bond_create_lc(self):
        self.ensure_one()
        if self.lc_id:
            raise UserError(_('This order already has an LC.'))
        lc = self.env['nelsis.lc'].create({
            'partner_id': self.partner_id.commercial_partner_id.id,
            'currency_id': self.currency_id.id,
            'original_amount': self.amount_total,
            'pi_number': self.partner_ref or False,
            'company_id': self.company_id.id,
        })
        self.lc_id = lc
        return {'type': 'ir.actions.act_window', 'res_model': 'nelsis.lc', 'res_id': lc.id, 'view_mode': 'form'}

    def action_bond_create_commercial_file(self):
        self.ensure_one()
        if self.commercial_file_id:
            raise UserError(_('This order already has a commercial file.'))
        File = self.env['nelsis.commercial.file']
        vals = {'partner_id': self.partner_id.commercial_partner_id.id,
                'transaction_type': 'import_lc' if self.lc_id else 'import_non_lc',
                'company_id': self.company_id.id}
        if self.lc_id and 'nelsis.lc' in dict(File._lc_selection()):
            vals['lc_ref'] = 'nelsis.lc,%d' % self.lc_id.id
        file = File.create(vals)
        self.commercial_file_id = file
        return {'type': 'ir.actions.act_window', 'res_model': 'nelsis.commercial.file', 'res_id': file.id,
                'view_mode': 'form'}

    def action_bond_create_consignment(self):
        self.ensure_one()
        if self.bond_purchase_type != 'import_bonded' or self.state not in ('purchase', 'done'):
            raise UserError(_('Consignments are created from a confirmed bonded import order.'))
        lines = []
        for line in self._bond_product_lines():
            qty = line.bond_uncovered_qty
            if qty <= 0:
                continue
            uom = line.product_id.uom_id
            lines.append(Command.create({
                'product_id': line.product_id.id,
                'product_uom_id': uom.id,
                'declared_qty': line.product_uom._compute_quantity(qty, uom),
                'purchase_line_id': line.id,
            }))
        if not lines:
            raise UserError(_('Every line of this order is already declared on a consignment.'))
        lc = self.lc_id.sudo()
        vals = {'partner_id': self.partner_id.commercial_partner_id.id, 'purchase_order_id': self.id,
                'company_id': self.company_id.id, 'line_ids': lines}
        if lc:
            vals['lc_number'] = lc.lc_number
            if 'nelsis.lc' in dict(self.env['bond.inventory.consignment']._selection_lc_models()):
                vals['lc_ref'] = 'nelsis.lc,%d' % lc.id
        cons = self.env['bond.inventory.consignment'].create(vals)
        return {'type': 'ir.actions.act_window', 'res_model': 'bond.inventory.consignment', 'res_id': cons.id,
                'view_mode': 'form'}

    # ------------------------------------------------------------------ smart buttons
    def action_view_bond_consignments(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Bond Consignments'),
                'res_model': 'bond.inventory.consignment', 'view_mode': 'tree,form',
                'domain': [('purchase_order_id', '=', self.id)]}

    def action_view_bond_receipts(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Bond Receipts'),
                'res_model': 'bond.inventory.receipt', 'view_mode': 'tree,form',
                'domain': [('purchase_order_id', '=', self.id)]}

    def action_view_lc(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'nelsis.lc', 'res_id': self.lc_id.id,
                'view_mode': 'form'}

    def action_view_commercial_file(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'nelsis.commercial.file',
                'res_id': self.commercial_file_id.id, 'view_mode': 'form'}

    # ------------------------------------------------------------------ sync
    def action_bond_sync(self):
        done = 0
        for po in self:
            done += po._bond_sync_links()
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Bond data synchronised'),
                           'message': _('%s record(s) aligned with the LC, commercial file and bond receipts.', done),
                           'type': 'success', 'sticky': False}}

    def _bond_sync_links(self):
        """Idempotent alignment of consignments, receipts, transfers, LC and commercial file. Returns the
        number of changes made. Runs with sudo: the button is limited to purchase users."""
        self.ensure_one()
        po = self.sudo()
        changes = 0
        lc = po.lc_id
        lines_by_key = {}
        for line in po._bond_product_lines():
            lines_by_key.setdefault((line.product_id.id, line.product_uom.category_id.id), line)
        for cons in po.bond_consignment_ids.filtered(lambda c: c.state != 'cancelled'):
            for cl in cons.line_ids.filtered(lambda l: not l.purchase_line_id):
                pol = lines_by_key.get((cl.product_id.id, cl.product_uom_id.category_id.id))
                if pol:
                    cl.purchase_line_id = pol
                    changes += 1
            if lc and cons.state == 'draft' and not cons.lc_ref and not cons.lc_number:
                cons.write({'lc_number': lc.lc_number})
                changes += 1
        for rec in po.bond_receipt_ids.filtered(lambda r: r.state == 'done'):
            changes += rec._bond_sync_done_receipt()
        file = po.commercial_file_id
        if file and lc and not file.lc_ref and 'nelsis.lc' in dict(file._lc_selection()):
            file.lc_ref = 'nelsis.lc,%d' % lc.id
            changes += 1
        return changes
