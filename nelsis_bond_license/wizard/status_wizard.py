# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import _, fields, models
from odoo.exceptions import UserError

ALLOWED_MODELS = (
    'bond.warehouse.license',
    'bond.warehouse.license.renewal',
    'bond.warehouse.security',
    'bond.warehouse.entitlement',
    'bond.warehouse.entitlement.amendment',
    'bond.warehouse.entitlement.utilization',
)


class BondWarehouseStatusWizard(models.TransientModel):
    _name = 'bond.warehouse.status.wizard'
    _description = 'Bond Warehouse Status Change'

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    action_code = fields.Char(required=True)
    action_label = fields.Char(readonly=True)
    change_date = fields.Date(string='Effective Date', required=True, default=fields.Date.context_today)
    reason = fields.Text(required=True)

    def action_confirm(self):
        self.ensure_one()
        if self.res_model not in ALLOWED_MODELS:
            raise UserError(_('This action is not supported for the selected record type.'))
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            raise UserError(_('The record no longer exists.'))
        record.check_access_rights('write')
        record.check_access_rule('write')
        record._bond_require_manager()
        record._bond_apply_status(self.action_code, self.reason, self.change_date)
        return {'type': 'ir.actions.act_window_close'}
