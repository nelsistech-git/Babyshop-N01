# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    bond_hs_code = fields.Char(
        string='HS Code (Bond)', index=True,
        help="Harmonized System code used by the bond register and reports.")
