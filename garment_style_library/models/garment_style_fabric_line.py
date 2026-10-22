# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentStyleFabricLine(models.Model):
    _name = 'garment.style.fabric.line'
    _description = 'Garment Style Fabric Specification Line'
    _order = 'sequence'

    style_id = fields.Many2one('garment.style', string='Style', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    fabric_role = fields.Selection([
        ('main', 'Main Fabric'), ('contrast', 'Contrast Fabric'), ('rib', 'Rib'), ('lining', 'Lining'),
        ('pocketing', 'Pocketing'), ('mesh', 'Mesh'), ('fleece', 'Fleece'), ('interlining', 'Interlining'),
    ], string='Fabric Role', required=True)
    composition = fields.Char(string='Composition')
    gsm = fields.Char(string='GSM')
    width = fields.Char(string='Width')
    weight = fields.Char(string='Weight')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    mill = fields.Char(string='Mill')
    country_of_origin_id = fields.Many2one('res.country', string='Country of Origin')
