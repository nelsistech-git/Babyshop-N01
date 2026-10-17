# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed
"""Single source of truth for the bond classification of a location.

Three modules each keep their own selection on ``stock.location``:

* nelsis_bond_inventory       ``bond_status``          (approved through a Classification Request)
* nelsis_bond_movement        ``bond_classification``  (used by bond movements)
* nelsis_bond_reconciliation  ``bond_scope``           (used by the register, ledger and reports)

Left alone they can disagree. The Bond Inventory status is the controlled one
(it needs an approved request with evidence), so it is authoritative and the other
two are derived from it whenever it changes.
"""
from odoo import _, api, models
from odoo.exceptions import UserError

SYNC_TRIGGER_FIELDS = {'bond_status', 'usage'}
DERIVED_FIELDS = {'bond_classification', 'bond_scope'}


class StockLocation(models.Model):
    _inherit = 'stock.location'

    def _bond_suite_derived_values(self):
        """Values of the derived classification fields for one location."""
        self.ensure_one()
        if self.bond_status == 'bonded':
            return {'bond_classification': 'bonded', 'bond_scope': 'bonded'}
        if self.usage == 'internal':
            return {'bond_classification': 'non_bonded', 'bond_scope': 'non_bonded'}
        return {'bond_classification': 'unclassified', 'bond_scope': 'none'}

    def _bond_suite_sync(self):
        """Align the derived fields with ``bond_status`` (only writes real differences)."""
        for loc in self.with_context(bond_suite_sync=True, active_test=False):
            target = loc._bond_suite_derived_values()
            vals = {k: v for k, v in target.items() if loc[k] != v}
            if vals:
                loc.sudo().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._bond_suite_sync()
        return records

    def write(self, vals):
        if (DERIVED_FIELDS & set(vals) and not self.env.su
                and not self.env.context.get('bond_suite_sync')):
            raise UserError(_(
                'The bond classification of a location follows its Bond Status. '
                'Change it through an approved Bond Classification Request '
                '(Bond Inventory), not directly.'))
        res = super().write(vals)
        if SYNC_TRIGGER_FIELDS & set(vals) and not self.env.context.get('bond_suite_sync'):
            self._bond_suite_sync()
        return res
