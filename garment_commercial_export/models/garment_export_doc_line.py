# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Commercial Invoice product-line detail (SRS section 23) —
garment.export.doc.line. Line detail for a
garment.export.documentation record of document_type = 'export_invoice'."""
from odoo import api, fields, models


class GarmentExportDocLine(models.Model):
    _name = 'garment.export.doc.line'
    _description = 'Garment Export Document Line (Invoice Product Detail)'
    _order = 'document_id, sequence'

    document_id = fields.Many2one('garment.export.documentation', string='Export Document', required=True,
                                   ondelete='cascade')
    sequence = fields.Integer(default=10)
    style_id = fields.Many2one('garment.style', string='Style')
    color = fields.Char(string='Color')
    size = fields.Char(string='Size')
    quantity = fields.Integer(string='Quantity')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    amount = fields.Monetary(string='Amount', compute='_compute_amount', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='document_id.currency_id', store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.quantity * rec.unit_price
