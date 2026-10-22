# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentSupplierPriceHistory(models.Model):
    """Supplier Price Management — Price History (SRS section 13):
    keeps a dated log of unit prices per supplier product/material so
    year-over-year price movement (e.g. Cotton Jersey $4.50/KG in 2026,
    $4.80/KG in 2027) can be tracked, instead of only the latest price."""
    _name = 'garment.supplier.price.history'
    _description = 'Garment Supplier Price History'
    _order = 'effective_date desc'

    supplier_product_id = fields.Many2one('garment.supplier.product', string='Supplier Product',
                                           required=True, ondelete='cascade')
    supplier_id = fields.Many2one('garment.supplier', string='Supplier',
                                   related='supplier_product_id.supplier_id', store=True)
    material_name = fields.Char(string='Material', related='supplier_product_id.product_name', store=True)
    price = fields.Monetary(string='Unit Price', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', related='supplier_product_id.currency_id', store=True)
    effective_date = fields.Date(string='Effective Date', required=True, default=fields.Date.context_today)
    validity_date = fields.Date(string='Validity')
    moq = fields.Float(string='MOQ')
    notes = fields.Char(string='Notes')
