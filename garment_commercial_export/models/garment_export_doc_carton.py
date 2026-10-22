# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Packing List carton-level detail (SRS section 24) —
garment.export.doc.carton. Carton detail for a
garment.export.documentation record of document_type = 'packing_list'."""
from odoo import fields, models


class GarmentExportDocCarton(models.Model):
    _name = 'garment.export.doc.carton'
    _description = 'Garment Export Document Carton (Packing List Detail)'
    _order = 'document_id, carton_no'

    document_id = fields.Many2one('garment.export.documentation', string='Export Document', required=True,
                                   ondelete='cascade')
    carton_no = fields.Char(string='Carton Number', required=True)
    style_id = fields.Many2one('garment.style', string='Style')
    color = fields.Char(string='Color')
    size = fields.Char(string='Size')
    quantity = fields.Integer(string='Quantity (PCS)')
    net_weight = fields.Float(string='Net Weight (KG)')
    gross_weight = fields.Float(string='Gross Weight (KG)')
    measurement = fields.Char(string='Measurement (L x W x H)')
