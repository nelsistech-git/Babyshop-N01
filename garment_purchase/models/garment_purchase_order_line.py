# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentPurchaseOrderLine(models.Model):
    _name = 'garment.purchase.order.line'
    _description = 'Garment Purchase Order Line'
    _order = 'sequence'

    order_id = fields.Many2one('garment.purchase.order', string='Purchase Order', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    material_category = fields.Selection([
        ('fabric', 'Fabric'), ('trim', 'Trim/Accessory'), ('packaging', 'Packaging'), ('other', 'Other'),
    ], string='Material Category', default='other')
    material_name = fields.Char(string='Material / Product', required=True)
    specification = fields.Char(string='Specification')
    quantity = fields.Float(string='Quantity', required=True)
    uom = fields.Char(string='UoM')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', store=True)
    line_total = fields.Monetary(string='Line Total', compute='_compute_line_total', store=True,
                                  currency_field='currency_id')
    delivery_date = fields.Date(string='Delivery Date')
    order_date = fields.Date(string='Order Date', related='order_id.order_date', store=True,
                              help='Denormalized for Material Cost Trend reporting (SRS section 38).')
    supplier_id = fields.Many2one('res.partner', related='order_id.supplier_id', store=True,
                                   string='Supplier (Order)')

    # Purchase Cost Analysis (SRS section 45): Saving % = (Previous Price -
    # Current Price) / Previous Price x 100.
    previous_price = fields.Monetary(string='Previous Price (Same Supplier/Material)',
                                      compute='_compute_previous_price', currency_field='currency_id')
    saving_pct = fields.Float(string='Saving (%)', compute='_compute_previous_price')

    @api.depends('quantity', 'unit_price')
    def _compute_line_total(self):
        for rec in self:
            rec.line_total = (rec.quantity or 0.0) * (rec.unit_price or 0.0)

    @api.depends('order_id.supplier_id', 'material_name', 'order_id.order_date', 'unit_price')
    def _compute_previous_price(self):
        for rec in self:
            rec.previous_price = 0.0
            rec.saving_pct = 0.0
            if not (rec.order_id.supplier_id and rec.material_name and rec.order_id.order_date):
                continue
            domain = [
                ('order_id.supplier_id', '=', rec.order_id.supplier_id.id),
                ('material_name', '=', rec.material_name),
                ('order_id.order_date', '<', rec.order_id.order_date),
                ('order_id.status', 'not in', ('draft', 'cancelled')),
            ]
            if isinstance(rec.id, int):
                domain.append(('id', '!=', rec.id))
            previous_line = self.search(domain, order='order_date desc', limit=1)
            if previous_line and previous_line.unit_price:
                rec.previous_price = previous_line.unit_price
                rec.saving_pct = (previous_line.unit_price - rec.unit_price) / previous_line.unit_price * 100.0
