# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentMerchQuotationLine(models.Model):
    _name = 'garment.merch.quotation.line'
    _description = 'Garment Merchandising Quotation Line'
    _order = 'sequence'

    quotation_id = fields.Many2one('garment.merch.quotation', string='Quotation', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    style_id = fields.Many2one('garment.style', string='Style')
    quantity = fields.Integer(string='Quantity')
    fob_price = fields.Monetary(string='FOB Price', currency_field='currency_id')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='quotation_id.currency_id', store=True)
    total_value = fields.Monetary(string='Total Value', compute='_compute_total', store=True,
                                   currency_field='currency_id')
    delivery_date = fields.Date(string='Delivery Date')
    remarks = fields.Char(string='Remarks')

    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for rec in self:
            rec.total_value = (rec.quantity or 0) * (rec.unit_price or 0.0)
