# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError

GROUP_CONTROLLER = 'nelsis_bond_movement.group_bond_movement_controller'


class StockLocation(models.Model):
    _inherit = 'stock.location'

    bond_classification = fields.Selection(
        [('unclassified', 'Unclassified'),
         ('bonded', 'Bonded'),
         ('non_bonded', 'Non-Bonded')],
        string='Bond Classification', default='unclassified', required=True,
        help="Classification of stock held in this location. Only users in the "
             "Bond Classification Controller group can change it, and not while stock exists.")
    bond_movement_allowed = fields.Boolean(
        string='Authorized for Bond Movements', default=False,
        help="Only authorized internal locations can be used as source or destination "
             "in bond movements.")

    def write(self, vals):
        # Suite core (nelsis_bond_warehouse) derives the classification from the approved
        # Bond Status of Bond Inventory and passes this context key; nothing else sets it.
        if self.env.context.get('bond_suite_sync'):
            return super().write(vals)
        if 'bond_classification' in vals or 'bond_movement_allowed' in vals:
            if not self.env.su and not self.env.user.has_group(GROUP_CONTROLLER):
                raise AccessError(_("Only a Bond Classification Controller can change bond settings on locations."))
            if 'bond_classification' in vals:
                for loc in self.filtered(lambda l: l.bond_classification != vals['bond_classification']):
                    has_stock = self.env['stock.quant'].sudo().search_count([
                        ('location_id', 'child_of', loc.id), ('quantity', '!=', 0)])
                    if has_stock:
                        raise UserError(_(
                            "Location %s holds stock. Reclassify stock through an approved bond "
                            "transfer instead of changing the location classification.", loc.display_name))
        return super().write(vals)
