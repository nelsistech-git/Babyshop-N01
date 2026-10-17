# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    bond_movement_id = fields.Many2one(
        'bond.warehouse.movement', string='Bond Movement', index=True,
        copy=False, readonly=True, ondelete='restrict',
        help="Source bond movement document. Used by the bond stock ledger for traceability.")
