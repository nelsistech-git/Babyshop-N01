# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, fields, models
from odoo.exceptions import UserError

MANAGER_GROUP = 'nelsis_bond_reconciliation.group_bond_recon_manager'


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    bond_adj_approved = fields.Boolean(string='Bond Adjustment Approved', copy=False, readonly=True)
    bond_adj_approved_by = fields.Many2one('res.users', string='Adjustment Approved By',
                                           copy=False, readonly=True)
    bond_adj_approved_on = fields.Datetime(string='Adjustment Approved On', copy=False, readonly=True)

    def action_bond_approve_adjustment(self):
        """Approve validated inventory adjustments for the bond register / reconciliation.

        The adjustment itself stays a normal Odoo stock move; this only records the
        bond approval (user + timestamp) so it is counted in reconciliations.
        """
        if not self.env.user.has_group(MANAGER_GROUP):
            raise UserError(_("Only a Bond Reconciliation Manager can approve bond adjustments."))
        lines = self.filtered(
            lambda l: l.state == 'done' and not l.bond_adj_approved
            and (l.move_id.is_inventory
                 or 'inventory' in (l.location_id.usage, l.location_dest_id.usage)))
        if not lines:
            raise UserError(_("Select validated inventory adjustment lines that are not approved yet."))
        lines.sudo().write({
            'bond_adj_approved': True,
            'bond_adj_approved_by': self.env.user.id,
            'bond_adj_approved_on': fields.Datetime.now(),
        })
        return True
