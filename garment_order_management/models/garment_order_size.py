# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentOrderSize(models.Model):
    """Size Ratio & Quantity Breakdown (SRS section 13) - garment.order.size.

    Example: 10,000 pcs with ratio S 20% / M 30% / L 30% / XL 20% ->
    quantities 2000 / 3000 / 3000 / 2000.
    """
    _name = 'garment.order.size'
    _description = 'Garment Order Size Breakdown'
    _order = 'order_line_id, sequence, id'

    order_line_id = fields.Many2one('garment.order.line', string='Order Line', required=True, ondelete='cascade')
    order_id = fields.Many2one(related='order_line_id.order_id', string='Order', store=True, readonly=True)
    sequence = fields.Integer(default=10)

    size_code = fields.Char(string='Size', required=True, help='e.g. S, M, L, XL, 32, 6Y')
    ratio_pct = fields.Float(string='Ratio (%)')
    quantity = fields.Integer(string='Quantity')

    @api.onchange('ratio_pct')
    def _onchange_ratio_pct(self):
        for rec in self:
            if rec.ratio_pct and rec.order_line_id and rec.order_line_id.quantity:
                rec.quantity = round(rec.order_line_id.quantity * rec.ratio_pct / 100.0)
