# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed
from odoo import api, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _bond_suite_fill_lc_ref(self):
        """Carry the LC number of the linked LC record (nelsis_lc_management) into the
        bond reference used by the register and reports (nelsis_bond_reconciliation).
        Only fills an empty reference on open transfers; never overwrites user input."""
        for picking in self.filtered(
                lambda p: p.lc_id and p.lc_id.lc_number and not p.bond_lc_ref
                and p.state not in ('done', 'cancel')):
            picking.bond_lc_ref = picking.lc_id.lc_number

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        pickings._bond_suite_fill_lc_ref()
        return pickings

    def write(self, vals):
        res = super().write(vals)
        if 'lc_id' in vals:
            self._bond_suite_fill_lc_ref()
        return res
