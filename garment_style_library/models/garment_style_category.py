# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentStyleCategory(models.Model):
    _name = 'garment.style.category'
    _description = 'Garment Style Product Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(string='Category Code', size=6,
                        help='Short code used as the product-category component of the Style Number, '
                             'e.g. KN for Knit, WV for Woven (SRS section 7: ST-2026-KN-000001).')
    sequence = fields.Integer(default=10)
    classification = fields.Selection([
        ('knit', 'Knit'), ('woven', 'Woven'), ('sweater', 'Sweater'), ('denim', 'Denim'),
        ('home_textile', 'Home Textile'), ('sportswear', 'Sportswear'), ('outerwear', 'Outerwear'),
        ('lingerie', 'Lingerie'), ('uniform', 'Uniform'), ('kidswear', 'Kidswear'),
    ], string='Product Classification')
    active = fields.Boolean(default=True)
