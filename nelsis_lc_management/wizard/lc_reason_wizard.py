# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import fields, models, _
from odoo.exceptions import UserError

# action_type -> (model, private method).  Each method re-checks the caller's
# group, so the wizard grants no extra privilege.
REASON_ACTIONS = {
    'lc_reject': ('nelsis.lc', '_do_reject'),
    'lc_hold': ('nelsis.lc', '_do_hold'),
    'lc_cancel': ('nelsis.lc', '_do_cancel'),
    'shipment_cancel': ('nelsis.lc.shipment', '_do_cancel'),
    'amendment_reject': ('nelsis.lc.amendment', '_do_reject'),
    'boe_cancel': ('nelsis.lc.boe', '_do_cancel'),
    'document_waive': ('nelsis.lc.document', '_do_waive'),
}


class NelsisLcReasonWizard(models.TransientModel):
    _name = 'nelsis.lc.reason.wizard'
    _description = 'LC Reason Wizard'

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    action_type = fields.Selection([(k, k) for k in REASON_ACTIONS], required=True)
    reason = fields.Text(required=True)

    def action_confirm(self):
        self.ensure_one()
        model, method = REASON_ACTIONS[self.action_type]
        if self.res_model != model:
            raise UserError(_('Invalid wizard request.'))
        reason = (self.reason or '').strip()
        if not reason:
            raise UserError(_('Please enter a reason.'))
        record = self.env[model].browse(self.res_id).exists()
        if not record:
            raise UserError(_('The record no longer exists.'))
        getattr(record, method)(reason)
        return {'type': 'ir.actions.act_window_close'}
