# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    bond_lc_ref = fields.Char(string='LC Reference', index=True, copy=False)
    bond_boe_ref = fields.Char(string='Bill of Entry Reference', index=True, copy=False)
    bond_license_ref = fields.Char(string='Bond License Reference', index=True, copy=False)
