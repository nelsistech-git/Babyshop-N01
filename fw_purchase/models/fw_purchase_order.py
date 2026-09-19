# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwPurchaseOrder(models.Model):
    _name = 'fw.purchase.order'
    _description = 'Footwear Purchase Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'order_date desc'

    name = fields.Char(string='PO Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.purchase.order') or 'New')
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True,
                                 domain="[('supplier_rank', '>', 0)]", tracking=True)
    rfq_id = fields.Many2one('fw.rfq', string='Source RFQ', readonly=True)

    order_date = fields.Date(string='Order Date', default=fields.Date.context_today)
    expected_date = fields.Date(string='Expected Delivery Date')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    line_ids = fields.One2many('fw.purchase.order.line', 'po_id', string='Order Lines')
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total', store=True,
                                    currency_field='currency_id')

    grn_ids = fields.One2many('fw.material.grn', 'po_id', string='Goods Received (GRN)')
    grn_count = fields.Integer(string='GRN Count', compute='_compute_grn_count')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent to Vendor'),
        ('confirmed', 'Confirmed'),
        ('partially_received', 'Partially Received'),
        ('received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.purchase.order') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    def _compute_grn_count(self):
        for rec in self:
            rec.grn_count = len(rec.grn_ids)

    def action_send(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Cannot send a Purchase Order with no lines.")
        self.write({'state': 'sent'})

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_grns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Goods Received',
            'res_model': 'fw.material.grn',
            'view_mode': 'tree,form',
            'domain': [('po_id', '=', self.id)],
            'context': {'default_po_id': self.id, 'default_supplier_id': self.vendor_id.id},
        }

    def _recompute_receipt_state(self):
        """Called by fw.material.grn when a GRN linked to this PO is confirmed, to keep
        the PO's status reflecting how much has actually been received."""
        for rec in self:
            ordered_qty = sum(rec.line_ids.mapped('qty'))
            received_qty = sum(rec.grn_ids.filtered(
                lambda g: g.state == 'inspected').mapped('accepted_qty'))
            if not ordered_qty or received_qty <= 0:
                continue
            if received_qty >= ordered_qty:
                rec.state = 'received'
            elif rec.state in ('confirmed', 'sent'):
                rec.state = 'partially_received'


class FwPurchaseOrderLine(models.Model):
    _name = 'fw.purchase.order.line'
    _description = 'Footwear Purchase Order Line'
    _order = 'id'

    po_id = fields.Many2one('fw.purchase.order', string='Purchase Order', required=True,
                             ondelete='cascade')
    material_description = fields.Char(string='Material Description', required=True)
    product_id = fields.Many2one('product.product', string='Product (if in catalog)')
    qty = fields.Float(string='Qty', required=True, default=0.0)
    uom_id = fields.Many2one('uom.uom', string='UoM',
                              default=lambda self: self.env.ref('uom.product_uom_unit', False))
    currency_id = fields.Many2one(related='po_id.currency_id', string='Currency', store=True)
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    amount = fields.Monetary(string='Amount', compute='_compute_amount', store=True,
                              currency_field='currency_id')

    @api.depends('qty', 'unit_price')
    def _compute_amount(self):
        for rec in self:
            rec.amount = (rec.qty or 0.0) * (rec.unit_price or 0.0)

    @api.constrains('qty', 'unit_price')
    def _check_non_negative(self):
        for rec in self:
            if rec.qty < 0:
                raise ValidationError("Purchase Order line quantity cannot be negative.")
            if rec.unit_price < 0:
                raise ValidationError("Purchase Order line unit price cannot be negative.")
