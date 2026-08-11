# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class InterCompanyTransfer(models.Model):
    _name = 'inter.company.transfer'
    _description = 'Inter-Company and Branch Stock Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Transfer Reference', required=True, copy=False,
        readonly=True, index=True, default=lambda self: _('New'))

    transfer_type = fields.Selection([
        ('company', 'Company to Company'),
        ('branch', 'Branch to Branch'),
    ], string='Transfer Type', default='company', required=True, tracking=True)

    source_company_id = fields.Many2one(
        'res.company', string='Source Company/Branch', required=True,
        default=lambda self: self.env.company, tracking=True)
    dest_company_id = fields.Many2one(
        'res.company', string='Destination Company/Branch', required=True, tracking=True)

    source_warehouse_id = fields.Many2one(
        'stock.warehouse', string='Source Warehouse', required=True,
        domain="[('company_id', '=', source_company_id)]")
    dest_warehouse_id = fields.Many2one(
        'stock.warehouse', string='Destination Warehouse', required=True,
        domain="[('company_id', '=', dest_company_id)]")

    line_ids = fields.One2many(
        'inter.company.transfer.line', 'transfer_id', string='Transfer Lines')

    purchase_order_id = fields.Many2one(
        'purchase.order', string='Generated PO', readonly=True, copy=False)
    sale_order_id = fields.Many2one(
        'sale.order', string='Generated SO', readonly=True, copy=False)

    picking_id = fields.Many2one(
        'stock.picking', string='Delivery Order', compute='_compute_picking_id',
        store=True, readonly=True)
    receipt_id = fields.Many2one(
        'stock.picking', string='Receipt', compute='_compute_receipt_id',
        store=True, readonly=True)

    # Live status of the delivery / receipt pickings, kept in sync so the
    # transfer document always reflects the real inventory state.
    delivery_state = fields.Selection(
        related='picking_id.state', string='Delivery Status', store=True, readonly=True)
    receipt_state = fields.Selection(
        related='receipt_id.state', string='Receipt Status', store=True, readonly=True)

    sync_delivery_receipt = fields.Boolean(
        string='Auto-Sync Delivery -> Receipt', default=True,
        help='When enabled, validating the Delivery Order automatically '
             'applies the same done quantities to the Receipt and validates '
             'it too, so the Sales Order, Purchase Order, Delivery and '
             'Receipt (and therefore both companies\' inventories) always '
             'stay in sync. When disabled, the Receipt must be validated '
             'manually.')

    create_invoice = fields.Boolean(
        string='Create Invoice/Bill', default=True,
        help='Automatically create the Customer Invoice (source company) '
             'and Vendor Bill (destination company) once the transfer is Done.')
    validate_invoice = fields.Boolean(
        string='Validate Invoice/Bill', default=False,
        help='Automatically post (validate) the generated Invoice and Bill. '
             'When disabled they are created in draft for accounting to review.')
    invoice_id = fields.Many2one(
        'account.move', string='Customer Invoice', readonly=True, copy=False)
    bill_id = fields.Many2one(
        'account.move', string='Vendor Bill', readonly=True, copy=False)
    invoice_state = fields.Selection(
        related='invoice_id.state', string='Invoice Status', readonly=True)
    bill_state = fields.Selection(
        related='bill_id.state', string='Bill Status', readonly=True)

    reversal_of_id = fields.Many2one(
        'inter.company.transfer', string='Return Of', readonly=True,
        copy=False, help='The original transfer this record reverses.')
    reversal_ids = fields.One2many(
        'inter.company.transfer', 'reversal_of_id', string='Return Transfers',
        readonly=True)
    reversal_count = fields.Integer(
        string='Return Count', compute='_compute_reversal_count')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    company_id = fields.Many2one(
        'res.company', string='Responsible Company', required=True,
        default=lambda self: self.env.company)
    user_id = fields.Many2one(
        'res.users', string='Responsible', default=lambda self: self.env.user)
    note = fields.Text(string='Notes')

    # ---------------------------------------------------------------------
    # Computes / Constraints
    # ---------------------------------------------------------------------
    @api.depends('sale_order_id.picking_ids', 'sale_order_id.picking_ids.state')
    def _compute_picking_id(self):
        for rec in self:
            rec.picking_id = rec.sale_order_id.picking_ids[:1]

    @api.depends('purchase_order_id.picking_ids', 'purchase_order_id.picking_ids.state')
    def _compute_receipt_id(self):
        for rec in self:
            rec.receipt_id = rec.purchase_order_id.picking_ids[:1]

    def _compute_reversal_count(self):
        for rec in self:
            rec.reversal_count = len(rec.reversal_ids)

    @api.constrains('source_company_id', 'dest_company_id')
    def _check_companies_differ(self):
        for rec in self:
            if rec.source_company_id and rec.dest_company_id \
                    and rec.source_company_id == rec.dest_company_id:
                raise ValidationError(_(
                    'Source Company/Branch and Destination Company/Branch '
                    'must not be the same.'))

    @api.constrains('line_ids')
    def _check_lines(self):
        for rec in self:
            if rec.state != 'draft' and not rec.line_ids:
                raise ValidationError(_('Please add at least one transfer line.'))

    # ---------------------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'inter.company.transfer') or _('New')
        return super().create(vals_list)

    # ---------------------------------------------------------------------
    # Business logic
    # ---------------------------------------------------------------------
    def action_confirm_transfer(self):
        """Generate the linked Sales Order (source company) and
        Purchase Order (destination company) and move the document
        to the 'confirmed' (In Progress) state."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft transfers can be confirmed.'))
            if not rec.line_ids:
                raise UserError(_('Please add at least one transfer line before confirming.'))

            sale_order = rec._create_sale_order()
            purchase_order = rec._create_purchase_order()

            rec.write({
                'sale_order_id': sale_order.id,
                'purchase_order_id': purchase_order.id,
                'state': 'confirmed',
            })
            rec.message_post(body=_(
                'Transfer confirmed. Sales Order %(so)s and Purchase Order '
                '%(po)s have been generated.',
                so=sale_order.name, po=purchase_order.name))
        return True

    def _get_source_partner(self):
        """Partner representing the Destination company, used as the
        Customer on the Source company's Sales Order."""
        self.ensure_one()
        partner = self.dest_company_id.partner_id
        if not partner:
            raise UserError(_(
                'Destination Company/Branch "%s" has no related partner '
                'configured.') % self.dest_company_id.name)
        return partner

    def _get_dest_partner(self):
        """Partner representing the Source company, used as the
        Vendor on the Destination company's Purchase Order."""
        self.ensure_one()
        partner = self.source_company_id.partner_id
        if not partner:
            raise UserError(_(
                'Source Company/Branch "%s" has no related partner '
                'configured.') % self.source_company_id.name)
        return partner

    def _create_sale_order(self):
        self.ensure_one()
        SaleOrder = self.env['sale.order'].with_company(self.source_company_id)
        order_lines = []
        for line in self.line_ids:
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.get_product_multiline_description_sale()
                        if hasattr(line.product_id, 'get_product_multiline_description_sale')
                        else line.product_id.display_name,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom_id.id,
            }))
        sale_order = SaleOrder.create({
            'partner_id': self._get_source_partner().id,
            'company_id': self.source_company_id.id,
            'warehouse_id': self.source_warehouse_id.id,
            'origin': self.name,
            'order_line': order_lines,
        })
        sale_order.action_confirm()
        return sale_order

    def _create_purchase_order(self):
        self.ensure_one()
        PurchaseOrder = self.env['purchase.order'].with_company(self.dest_company_id)
        order_lines = []
        for line in self.line_ids:
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.display_name,
                'product_qty': line.product_uom_qty,
                'product_uom': line.product_uom_id.id,
                'date_planned': fields.Datetime.now(),
                'price_unit': line.product_id.standard_price,
            }))
        purchase_order = PurchaseOrder.create({
            'partner_id': self._get_dest_partner().id,
            'company_id': self.dest_company_id.id,
            'picking_type_id': self.dest_warehouse_id.in_type_id.id,
            'origin': self.name,
            'order_line': order_lines,
        })
        purchase_order.button_confirm()
        return purchase_order

    def action_done(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_('Only in-progress transfers can be marked as done.'))
            rec.state = 'done'
            rec._generate_invoices()

    # ---------------------------------------------------------------------
    # Delivery <-> Receipt <-> Inventory synchronization
    # ---------------------------------------------------------------------
    def _sync_receipt_from_delivery(self, delivery_picking):
        """Mirror the quantities actually delivered onto the linked receipt
        and validate it, so the destination inventory is updated with the
        exact quantities that left the source inventory (handles partial
        deliveries / backorders correctly)."""
        self.ensure_one()
        receipt = self.receipt_id
        if not receipt or receipt.state in ('done', 'cancel'):
            return

        delivered_by_product = {}
        for move in delivery_picking.move_ids.filtered(lambda m: m.state == 'done'):
            delivered_by_product[move.product_id.id] = \
                delivered_by_product.get(move.product_id.id, 0.0) + move.quantity

        pending_moves = receipt.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        for move in pending_moves:
            qty = delivered_by_product.get(move.product_id.id, 0.0)
            if qty <= 0:
                continue
            move.quantity = min(qty, move.product_uom_qty) if move.product_uom_qty else qty
            move.picked = True

        # Validate without popping the backorder wizard - any undelivered
        # remainder on the SO side will generate its own backorder delivery,
        # which will re-trigger this sync when it is validated.
        receipt.with_context(
            skip_backorder=True,
            picking_ids_not_to_backorder=receipt.ids,
        ).button_validate()

    def _check_auto_done(self):
        """Automatically close the transfer once both the delivery and the
        receipt are fully validated, keeping SO/PO/Delivery/Receipt/state
        all in sync without requiring a manual 'Mark as Done' click."""
        self.ensure_one()
        if self.state == 'confirmed' and self.delivery_state == 'done' \
                and self.receipt_state == 'done':
            self.state = 'done'
            self.message_post(body=_(
                'Delivery and Receipt have both been fully validated - '
                'transfer automatically marked as Done.'))
            # Invoice/Bill generation must never block the physical
            # inventory flow: if accounting isn't configured yet (missing
            # journal, fiscal position, etc.) the delivery/receipt should
            # still validate successfully. Failures are logged on the
            # transfer instead of raised, and can be retried manually.
            try:
                with self.env.cr.savepoint():
                    self._generate_invoices()
            except Exception as exc:  # noqa: BLE001
                self.message_post(body=_(
                    'Transfer completed, but automatic Invoice/Bill '
                    'generation failed: %(error)s. You can retry from the '
                    '"Create Invoice/Bill" button once resolved.',
                    error=str(exc)))

    # ---------------------------------------------------------------------
    # Invoice / Bill generation
    # ---------------------------------------------------------------------
    def _generate_invoices(self):
        """Create the Customer Invoice on the source company's Sales Order
        and the Vendor Bill on the destination company's Purchase Order,
        keeping the accounting side in sync with the physical transfer."""
        self.ensure_one()
        if not self.create_invoice:
            return

        if self.sale_order_id and not self.invoice_id:
            invoices = self.sale_order_id.with_company(
                self.source_company_id)._create_invoices()
            if invoices:
                invoice = invoices[0]
                if self.validate_invoice:
                    invoice.with_company(self.source_company_id).action_post()
                self.invoice_id = invoice.id

        if self.purchase_order_id and not self.bill_id:
            po = self.purchase_order_id.with_company(self.dest_company_id)
            existing_bill_ids = po.invoice_ids.ids
            po.action_create_invoice()
            new_bill = po.invoice_ids.filtered(lambda m: m.id not in existing_bill_ids)
            if new_bill:
                bill = new_bill[0]
                if self.validate_invoice:
                    bill.with_company(self.dest_company_id).action_post()
                self.bill_id = bill.id

    def action_create_invoices(self):
        """Manual trigger, e.g. when 'Create Invoice/Bill' was left off or
        the automatic generation needs to be re-run."""
        for rec in self:
            if rec.state != 'done':
                raise UserError(_('Invoices/Bills can only be created for completed transfers.'))
            rec._generate_invoices()

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'context': {'allowed_company_ids': [self.source_company_id.id]},
        }

    def action_view_bill(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bill'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.bill_id.id,
            'context': {'allowed_company_ids': [self.dest_company_id.id]},
        }

    # ---------------------------------------------------------------------
    # Return / Reverse transaction
    # ---------------------------------------------------------------------
    def action_reverse_transfer(self):
        """Create a new transfer that mirrors this one with source and
        destination swapped, to send the goods (or part of them) back."""
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_('Only a fully completed transfer can be reversed.'))
        if self.reversal_ids:
            raise UserError(_('This transfer has already been reversed.'))
        if not self.line_ids:
            raise UserError(_('There are no lines to reverse.'))

        reversal = self.create({
            'transfer_type': self.transfer_type,
            'source_company_id': self.dest_company_id.id,
            'dest_company_id': self.source_company_id.id,
            'source_warehouse_id': self.dest_warehouse_id.id,
            'dest_warehouse_id': self.source_warehouse_id.id,
            'reversal_of_id': self.id,
            'create_invoice': self.create_invoice,
            'validate_invoice': self.validate_invoice,
            'sync_delivery_receipt': self.sync_delivery_receipt,
            'note': _('Return of transfer %s') % self.name,
            'line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.qty_received or line.product_uom_qty,
                'product_uom_id': line.product_uom_id.id,
            }) for line in self.line_ids],
        })
        self.message_post(body=_(
            'Return transfer %s was created.') % reversal.name)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return Transfer'),
            'res_model': 'inter.company.transfer',
            'view_mode': 'form',
            'res_id': reversal.id,
        }

    def action_view_reversals(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Return Transfers'),
            'res_model': 'inter.company.transfer',
            'context': {'default_reversal_of_id': self.id},
        }
        if len(self.reversal_ids) == 1:
            action.update({'view_mode': 'form', 'res_id': self.reversal_ids.id})
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.reversal_ids.ids)],
            })
        return action

    # ---------------------------------------------------------------------
    # Bulk line import (via the shared bulk_order_line_import wizard)
    # ---------------------------------------------------------------------
    def action_open_bulk_import_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Import Transfer Lines'),
            'res_model': 'inter.company.transfer.bulk.import',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_transfer_id': self.id,
            },
        }

    def action_cancel(self):
        for rec in self:
            if rec.sale_order_id and rec.sale_order_id.state not in ('cancel',):
                rec.sale_order_id.with_company(rec.source_company_id).action_cancel()
            if rec.purchase_order_id and rec.purchase_order_id.state not in ('cancel',):
                rec.purchase_order_id.with_company(rec.dest_company_id).button_cancel()
            if rec.invoice_id and rec.invoice_id.state == 'draft':
                rec.invoice_id.with_company(rec.source_company_id).button_cancel()
            if rec.bill_id and rec.bill_id.state == 'draft':
                rec.bill_id.with_company(rec.dest_company_id).button_cancel()
            rec.state = 'cancel'

    def action_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})

    # ---------------------------------------------------------------------
    # Smart button actions
    # ---------------------------------------------------------------------
    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'context': {'allowed_company_ids': [self.source_company_id.id]},
        }

    def action_view_purchase_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Order'),
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_order_id.id,
            'context': {'allowed_company_ids': [self.dest_company_id.id]},
        }

    def action_view_delivery(self):
        self.ensure_one()
        pickings = self.sale_order_id.picking_ids
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Delivery Orders'),
            'res_model': 'stock.picking',
            'context': {'allowed_company_ids': [self.source_company_id.id]},
        }
        if len(pickings) == 1:
            action.update({'view_mode': 'form', 'res_id': pickings.id})
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', pickings.ids)],
            })
        return action

    def action_view_receipt(self):
        self.ensure_one()
        pickings = self.purchase_order_id.picking_ids
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Receipts'),
            'res_model': 'stock.picking',
            'context': {'allowed_company_ids': [self.dest_company_id.id]},
        }
        if len(pickings) == 1:
            action.update({'view_mode': 'form', 'res_id': pickings.id})
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', pickings.ids)],
            })
        return action
