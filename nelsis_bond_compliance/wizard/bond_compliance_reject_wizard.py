# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
from odoo import _, fields, models
from odoo.exceptions import UserError

ALLOWED_MODELS = ('bond.compliance.rule', 'bond.compliance.exception')


class BondComplianceRejectWizard(models.TransientModel):
    _name = 'bond.compliance.reject.wizard'
    _description = 'Bond Compliance Rejection Wizard'

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm(self):
        self.ensure_one()
        if self.res_model not in ALLOWED_MODELS:
            raise UserError(_('Rejection is not supported for this record type.'))
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            raise UserError(_('The record no longer exists.'))
        record.action_reject(reason=self.reason)
        return {'type': 'ir.actions.act_window_close'}
