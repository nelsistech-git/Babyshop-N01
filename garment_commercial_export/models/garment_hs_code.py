# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""HS Code Management (SRS section 30) — garment.hs.code. Product/style
classification master used by Export Documentation, Customs Documentation
and the EXP Form for duty and country-rule reference."""
from odoo import fields, models


class GarmentHsCode(models.Model):
    _name = 'garment.hs.code'
    _description = 'Garment HS Code'
    _order = 'code'

    code = fields.Char(string='HS Code', required=True)
    description = fields.Char(string='Description', required=True)
    style_id = fields.Many2one('garment.style', string='Style')
    product_category_id = fields.Many2one('garment.style.category', string='Product Category')
    duty_rate = fields.Float(string='Duty Rate (%)')
    country_id = fields.Many2one('res.country', string='Country Rules For')
    notes = fields.Text(string='Country-Specific Rules / Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('hs_code_country_uniq', 'unique(code, country_id)', 'HS Code must be unique per country!'),
    ]

    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.code, rec.description)) for rec in self]
