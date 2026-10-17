# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import api, fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    bond_scope = fields.Selection(
        [('none', 'Inherit / Not Classified'),
         ('bonded', 'Bonded'),
         ('non_bonded', 'Non-Bonded')],
        string='Bond Classification', default='none', index=True,
        help="Classify this location as bonded or non-bonded. Child locations "
             "inherit the classification of the nearest classified parent.")
    bond_scope_effective = fields.Selection(
        [('none', 'Not Classified'),
         ('bonded', 'Bonded'),
         ('non_bonded', 'Non-Bonded')],
        string='Effective Bond Classification',
        compute='_compute_bond_scope_effective', store=True, recursive=True,
        index=True)

    @api.depends('bond_scope', 'location_id.bond_scope_effective')
    def _compute_bond_scope_effective(self):
        for loc in self:
            if loc.bond_scope and loc.bond_scope != 'none':
                loc.bond_scope_effective = loc.bond_scope
            else:
                loc.bond_scope_effective = loc.location_id.bond_scope_effective or 'none'
