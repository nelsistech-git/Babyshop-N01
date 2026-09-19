# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwColor(models.Model):
    _name = 'fw.color'
    _description = 'Footwear Color Master'
    _order = 'name'

    name = fields.Char(string='Color Name', required=True)
    code = fields.Char(string='Color Code', required=True, help="Internal or Pantone code")
    pantone_code = fields.Char(string='Pantone / TPX Code')
    color_swatch = fields.Char(string='Hex Swatch', default='#FFFFFF',
                                help="Hex color used for swatch display, e.g. #1A1A1A")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Color Code must be unique!'),
    ]

    def name_get(self):
        result = []
        for rec in self:
            label = "[%s] %s" % (rec.code, rec.name) if rec.code else rec.name
            result.append((rec.id, label))
        return result
