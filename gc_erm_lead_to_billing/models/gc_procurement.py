# -*- coding: utf-8 -*-
"""Procurement request and purchase integration (SRS 32 / 33)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

PR_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('purchase_pending', 'Purchase Pending'),
    ('rfq', 'RFQ Created'),
    ('po', 'PO Created'),
    ('partial', 'Partially Received'),
    ('received', 'Received'),
    ('cancelled', 'Cancelled'),
]


class GcErmProcurementRequest(models.Model):
    _name = 'gc.erm.procurement.request'
    _description = 'GC ERM Procurement Request'
    _inherit = ['gc.erm.document.mixin']
    _order = 'priority desc, required_date, id desc'

    _gc_sequence_code = 'gc.erm.procurement.request'
    _gc_sla_parameter = 'gc_erm.sla_procurement_days'
    _gc_closed_states = ('received', 'cancelled')

    state = fields.Selection(
        PR_STATE_SELECTION, string='Status', default='draft', required=True,
        copy=False, tracking=True, index=True, group_expand='_group_expand_state')

    work_order_id = fields.Many2one(
        'gc.erm.work.order', string='Work Order', required=True,
        ondelete='restrict', index=True, tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', related='work_order_id.partner_id',
        store=True, index=True)
    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order',
        related='work_order_id.sale_order_id', store=True)
    requested_by_id = fields.Many2one(
        'res.users', string='Requested By', required=True,
        default=lambda self: self.env.user, tracking=True)
    request_date = fields.Date(
        string='Request Date', default=fields.Date.context_today, required=True)
    required_date = fields.Date(string='Required Date', tracking=True)
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1', index=True, tracking=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        related='work_order_id.warehouse_id', store=True)
    remarks = fields.Text(string='Remarks')

    line_ids = fields.One2many(
        'gc.erm.procurement.line', 'request_id', string='Shortage Lines',
        copy=True)
    purchase_order_ids = fields.One2many(
        'purchase.order', 'gc_procurement_id', string='Purchase Orders')
    purchase_order_count = fields.Integer(compute='_compute_counts')
    picking_count = fields.Integer(compute='_compute_counts')

    total_shortage_qty = fields.Float(
        string='Total Shortage', compute='_compute_totals', store=True)
    total_received_qty = fields.Float(
        string='Total Received', compute='_compute_totals', store=True)
    estimated_amount = fields.Monetary(
        string='Estimated Amount', compute='_compute_totals', store=True,
        currency_field='currency_id')
    receipt_progress = fields.Float(
        string='Receipt Progress (%)', compute='_compute_totals', store=True)

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_state(self, states, domain, order=None):
        return [key for key, _label in PR_STATE_SELECTION]

    @api.depends('line_ids.shortage_qty', 'line_ids.received_qty',
                 'line_ids.estimated_price', 'line_ids.estimated_subtotal')
    def _compute_totals(self):
        for request in self:
            request.total_shortage_qty = sum(request.line_ids.mapped('shortage_qty'))
            request.total_received_qty = sum(request.line_ids.mapped('received_qty'))
            request.estimated_amount = sum(
                request.line_ids.mapped('estimated_subtotal'))
            request.receipt_progress = (
                request.total_received_qty / request.total_shortage_qty * 100.0
            ) if request.total_shortage_qty else 0.0

    def _compute_counts(self):
        for request in self:
            request.purchase_order_count = len(request.purchase_order_ids)
            request.picking_count = len(
                request.purchase_order_ids.mapped('picking_ids'))

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('required_date', 'request_date')
    def _check_dates(self):
        for request in self:
            if request.required_date and request.request_date and \
                    request.required_date < request.request_date:
                raise ValidationError(_(
                    'The required date cannot be before the request date.'))

    # ------------------------------------------------------------------
    # Workflow (SRS 32)
    # ------------------------------------------------------------------
    def action_submit(self):
        for request in self:
            if request.state != 'draft':
                raise UserError(_(
                    'Only a draft procurement request can be submitted.'))
            if not request.line_ids:
                raise UserError(_(
                    'Procurement request %s has no shortage lines.',
                    request.name))
            request._gc_transition(
                'submitted', comment=_('Procurement request submitted.'),
                allowed_from=('draft',),
                extra_vals={
                    'submitted_by_id': self.env.user.id,
                    'submitted_date': fields.Datetime.now(),
                })
            buyer = request._gc_first_user_in_group(
                'gc_erm_lead_to_billing.group_gc_purchase_user')
            if buyer:
                request._gc_schedule_activity(
                    buyer,
                    summary=_('Process procurement %s', request.name),
                    note=_('Work order %(wo)s needs %(qty).2f units.',
                           wo=request.work_order_id.name,
                           qty=request.total_shortage_qty),
                    days=int(request._gc_sla_days() or 1))
            request._gc_notify(
                'gc_erm_lead_to_billing.mail_template_gc_procurement_created')
        return True

    def action_accept(self):
        """Purchase department acknowledges the request."""
        for request in self:
            if request.state != 'submitted':
                raise UserError(_(
                    'Only a submitted request can be accepted by Purchase.'))
            request._gc_require_group(
                'gc_erm_lead_to_billing.group_gc_purchase_user',
                _('process procurement requests'))
            request._gc_transition(
                'purchase_pending', comment=_('Accepted by Purchase.'),
                allowed_from=('submitted',))
        return True

    def action_open_po_wizard(self):
        self.ensure_one()
        if self.state not in ('submitted', 'purchase_pending', 'rfq'):
            raise UserError(_(
                'RFQs can only be created for a submitted procurement request.'))
        self._gc_require_group(
            'gc_erm_lead_to_billing.group_gc_purchase_user',
            _('create requests for quotation'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Request for Quotation'),
            'res_model': 'gc.erm.procurement.po.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_mark_po_created(self):
        for request in self:
            if request.purchase_order_ids.filtered(
                    lambda p: p.state in ('purchase', 'done')):
                target = 'po'
            elif request.purchase_order_ids:
                target = 'rfq'
            else:
                continue
            if request.state != target:
                request._gc_transition(
                    target,
                    comment=_('Purchase documents updated.'))
        return True

    def action_check_receipt(self):
        """Refresh received quantities from the purchase receipts."""
        for request in self:
            request.line_ids._compute_received_qty()
            request._compute_totals()
            lines = request.line_ids
            if not lines:
                continue
            fully = all(
                float_compare(line.received_qty, line.shortage_qty,
                              precision_digits=4) >= 0 for line in lines)
            partially = any(
                not float_is_zero(line.received_qty, precision_digits=4)
                for line in lines)
            if fully and request.state not in ('received', 'cancelled'):
                request._gc_transition(
                    'received', comment=_('All materials received.'))
                request.work_order_id.action_check_inventory()
                request._gc_notify(
                    'gc_erm_lead_to_billing.mail_template_gc_material_received')
            elif partially and request.state not in ('partial', 'received',
                                                     'cancelled'):
                request._gc_transition(
                    'partial', comment=_('Materials partially received.'))
        return True

    def action_reset_draft(self):
        for request in self:
            if request.purchase_order_ids.filtered(
                    lambda p: p.state not in ('cancel',)):
                raise UserError(_(
                    'Cancel the related purchase documents of %s first.',
                    request.name))
            request._gc_transition('draft', comment=_('Reset to draft.'))
        return True

    def action_cancel(self):
        for request in self:
            if request.purchase_order_ids.filtered(
                    lambda p: p.state in ('purchase', 'done')):
                raise UserError(_(
                    'Procurement request %s has confirmed purchase orders.',
                    request.name))
            request.purchase_order_ids.filtered(
                lambda p: p.state in ('draft', 'sent')).button_cancel()
            request._gc_transition('cancelled', comment=_('Request cancelled.'))
        return True

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('gc_procurement_id', '=', self.id)],
        }

    def action_view_receipts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipts'),
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in',
                        self.purchase_order_ids.mapped('picking_ids').ids)],
        }

    def action_view_work_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gc.erm.work.order',
            'res_id': self.work_order_id.id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Cron (SRS 80 -- procurement aging)
    # ------------------------------------------------------------------
    @api.model
    def _cron_check_procurement_aging(self):
        today = fields.Date.context_today(self)
        overdue = self.search([
            ('state', 'in', ('submitted', 'purchase_pending', 'rfq', 'po',
                             'partial')),
            ('required_date', '<', today),
        ])
        for request in overdue:
            request.action_check_receipt()
            if request.state in ('received', 'cancelled'):
                continue
            buyer = request._gc_first_user_in_group(
                'gc_erm_lead_to_billing.group_gc_purchase_user')
            if buyer:
                request._gc_schedule_activity(
                    buyer, summary=_('Overdue procurement %s', request.name),
                    note=_('Required by %s.', request.required_date), days=0)
        return True


class GcErmProcurementLine(models.Model):
    _name = 'gc.erm.procurement.line'
    _description = 'GC ERM Procurement Line'
    _order = 'request_id, sequence, id'

    request_id = fields.Many2one(
        'gc.erm.procurement.request', string='Request', required=True,
        ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        related='request_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='request_id.currency_id', store=True)
    state = fields.Selection(related='request_id.state', string='Status')

    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
        domain="[('purchase_ok', '=', True)]")
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    required_qty = fields.Float(
        string='Required Qty', digits='Product Unit of Measure')
    available_qty = fields.Float(
        string='Available Qty', digits='Product Unit of Measure')
    shortage_qty = fields.Float(
        string='Shortage Qty', required=True, digits='Product Unit of Measure')
    ordered_qty = fields.Float(
        string='Ordered Qty', compute='_compute_ordered_qty',
        digits='Product Unit of Measure')
    received_qty = fields.Float(
        string='Received Qty', readonly=True, digits='Product Unit of Measure')
    vendor_id = fields.Many2one(
        'res.partner', string='Suggested Vendor',
        domain="[('supplier_rank', '>', 0)]")
    estimated_price = fields.Monetary(
        string='Estimated Unit Price', currency_field='currency_id')
    estimated_subtotal = fields.Monetary(
        string='Estimated Subtotal', compute='_compute_subtotal', store=True,
        currency_field='currency_id')
    work_order_line_id = fields.Many2one(
        'gc.erm.work.order.line', string='Work Order Line', ondelete='set null')
    purchase_line_ids = fields.One2many(
        'purchase.order.line', 'gc_procurement_line_id', string='Purchase Lines')
    remarks = fields.Char(string='Remarks')

    @api.depends('shortage_qty', 'estimated_price')
    def _compute_subtotal(self):
        for line in self:
            line.estimated_subtotal = line.shortage_qty * line.estimated_price

    @api.depends('purchase_line_ids.product_qty', 'purchase_line_ids.state')
    def _compute_ordered_qty(self):
        for line in self:
            line.ordered_qty = sum(line.purchase_line_ids.filtered(
                lambda p: p.state not in ('cancel',)).mapped('product_qty'))

    def _compute_received_qty(self):
        for line in self:
            line.received_qty = sum(line.purchase_line_ids.filtered(
                lambda p: p.state not in ('cancel',)).mapped('qty_received'))
        return True

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            product = line.product_id
            if not product:
                continue
            line.description = product.display_name
            line.uom_id = product.uom_po_id or product.uom_id
            line.estimated_price = product.standard_price
            seller = product.seller_ids[:1]
            if seller:
                line.vendor_id = seller.partner_id
                line.estimated_price = seller.price or product.standard_price

    @api.constrains('shortage_qty')
    def _check_shortage(self):
        for line in self:
            if float_compare(line.shortage_qty, 0.0, precision_digits=4) <= 0:
                raise ValidationError(_(
                    'The shortage quantity of "%s" must be greater than zero.',
                    line.product_id.display_name))
