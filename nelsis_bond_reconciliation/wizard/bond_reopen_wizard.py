# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, fields, models
from odoo.exceptions import UserError


class BondReconciliationReopenWizard(models.TransientModel):
    _name = 'bond.reconciliation.reopen.wizard'
    _description = 'Reopen Bond Reconciliation'

    reconciliation_id = fields.Many2one('bond.warehouse.reconciliation', required=True, readonly=True)
    reason = fields.Text(string='Reason for Reopening', required=True)

    def action_confirm(self):
        self.ensure_one()
        rec = self.reconciliation_id
        rec._check_manager()
        reason = (self.reason or '').strip()
        if len(reason) < 5:
            raise UserError(_("Please enter a meaningful reason for reopening."))
        if rec.state not in ('reconciled', 'closed'):
            raise UserError(_("Only Reconciled or Closed records can be reopened."))
        self.env['bond.warehouse.reconciliation.reopen'].sudo().create({
            'reconciliation_id': rec.id,
            'user_id': self.env.user.id,
            'from_state': rec.state,
            'reason': reason,
        })
        rec.write({
            'state': 'in_progress',
            'approver_id': False, 'approved_on': False,
            'reviewer_id': False, 'reviewed_on': False,
            'closed_on': False,
        })
        rec.message_post(body=_("Reopened by %(user)s. Reason: %(reason)s",
                                user=self.env.user.name, reason=reason))
        return {'type': 'ir.actions.act_window_close'}
