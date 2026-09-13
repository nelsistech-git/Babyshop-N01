# -*- coding: utf-8 -*-
"""Create RFQs / purchase orders from a procurement request (SRS 33)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class GcErmProcurementPoWizard(models.TransientModel):
    _name = 'gc.erm.procurement.po.wizard'
    _description = 'GC ERM Procurement to RFQ'

    request_id = fields.Many2one(
        'gc.erm.procurement.request', string='Procurement Request',
        required=True, readonly=True)
    vendor_id = fields.Many2one(
        'res.partner', string='Vendor', required=True,
        domain="[('supplier_rank', '>', 0)]",
        help='All selected lines are grouped into one RFQ for this vendor.')
    date_planned = fields.Datetime(
        string='Expected Arrival', required=True,
        default=fields.Datetime.now)
    line_ids = fields.Many2many(
        'gc.erm.procurement.line', string='Lines to Order')
    confirm_order = fields.Boolean(
        string='Confirm the Purchase Order immediately', default=False)
    note = fields.Text(string='Note to Vendor')

    @api.onchange('request_id')
    def _onchange_request_id(self):
        for wizard in self:
            if not wizard.request_id:
                continue
            pending = wizard.request_id.line_ids.filtered(
                lambda l: l.shortage_qty > l.ordered_qty)
            wizard.line_ids = [(6, 0, pending.ids)]
            vendors = pending.mapped('vendor_id')
            if len(vendors) == 1:
                wizard.vendor_id = vendors

    def action_create_rfq(self):
        self.ensure_one()
        request = self.request_id
        lines = self.line_ids or request.line_ids
        if not lines:
            raise UserError(_('Select at least one line to order.'))
        order_lines = []
        for line in lines:
            remaining = line.shortage_qty - line.ordered_qty
            if remaining <= 0:
                continue
            product = line.product_id
            order_lines.append((0, 0, {
                'product_id': product.id,
                'name': line.description or product.display_name,
                'product_qty': remaining,
                'product_uom': (line.uom_id or product.uom_po_id
                                or product.uom_id).id,
                'price_unit': line.estimated_price or product.standard_price,
                'date_planned': self.date_planned,
                'gc_procurement_line_id': line.id,
            }))
        if not order_lines:
            raise UserError(_(
                'Every selected line has already been fully ordered.'))
        purchase = self.env['purchase.order'].create({
            'partner_id': self.vendor_id.id,
            'company_id': request.company_id.id,
            'currency_id': request.currency_id.id,
            'date_order': fields.Datetime.now(),
            'date_planned': self.date_planned,
            'origin': request.name,
            'notes': self.note or False,
            'gc_procurement_id': request.id,
            'gc_work_order_id': request.work_order_id.id,
            'picking_type_id': self._get_picking_type(request).id,
            'order_line': order_lines,
        })
        if self.confirm_order:
            purchase.button_confirm()
        request.action_mark_po_created()
        request.message_post(body=_(
            'Request for quotation %(po)s created for %(vendor)s.',
            po=purchase.name, vendor=self.vendor_id.display_name))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request for Quotation'),
            'res_model': 'purchase.order',
            'res_id': purchase.id,
            'view_mode': 'form',
        }

    def _get_picking_type(self, request):
        warehouse = request.warehouse_id or self.env['stock.warehouse'].search(
            [('company_id', '=', request.company_id.id)], limit=1)
        if warehouse and warehouse.in_type_id:
            return warehouse.in_type_id
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('company_id', '=', request.company_id.id),
        ], limit=1)
        if not picking_type:
            raise UserError(_(
                'No incoming operation type is configured for company %s.',
                request.company_id.display_name))
        return picking_type
