# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import fields, models


class BondMovementReverse(models.TransientModel):
    _name = 'bond.warehouse.movement.reverse'
    _description = 'Reverse Bond Movement'

    movement_id = fields.Many2one('bond.warehouse.movement', required=True, readonly=True)
    reason = fields.Text(string='Reversal Reason', required=True)

    def action_confirm(self):
        self.ensure_one()
        self.movement_id.action_reverse(self.reason)
        return {'type': 'ir.actions.act_window_close'}
