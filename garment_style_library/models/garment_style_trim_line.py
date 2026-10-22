# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentStyleTrimLine(models.Model):
    _name = 'garment.style.trim.line'
    _description = 'Garment Style Trim Specification Line'
    _order = 'sequence'

    style_id = fields.Many2one('garment.style', string='Style', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    trim_type = fields.Selection([
        ('thread', 'Thread'), ('button', 'Buttons'), ('snap', 'Snaps'), ('zipper', 'Zippers'),
        ('elastic', 'Elastic'), ('label', 'Labels'), ('hang_tag', 'Hang Tags'), ('poly_bag', 'Poly Bags'),
        ('carton', 'Cartons'), ('drawcord', 'Drawcord'), ('eyelet', 'Eyelets'), ('accessory', 'Accessories'),
    ], string='Trim Type', required=True)
    description = fields.Char(string='Description')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    color = fields.Char(string='Color')
    size_spec = fields.Char(string='Size / Spec')
