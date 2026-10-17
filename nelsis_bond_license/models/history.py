# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import _, fields, models
from odoo.exceptions import UserError


class BondWarehouseHistory(models.Model):
    _name = 'bond.warehouse.history'
    _description = 'Bond Warehouse Audit Trail'
    _order = 'id desc'

    res_model = fields.Char(required=True, index=True, readonly=True)
    res_id = fields.Many2oneReference(model_field='res_model', required=True, index=True, readonly=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True,
                                 default=lambda self: self.env.company)
    event = fields.Char(required=True, readonly=True)
    from_state = fields.Char(readonly=True)
    to_state = fields.Char(readonly=True)
    note = fields.Text(readonly=True)
    event_date = fields.Date(string='Effective Date', readonly=True,
                             default=fields.Date.context_today)
    user_id = fields.Many2one('res.users', string='User', required=True, readonly=True,
                              default=lambda self: self.env.user)
    timestamp = fields.Datetime(readonly=True, default=fields.Datetime.now)

    def write(self, vals):
        raise UserError(_('Audit trail entries cannot be modified.'))

    def unlink(self):
        if not self.env.context.get('bond_history_cleanup'):
            raise UserError(_('Audit trail entries cannot be deleted.'))
        return super().unlink()
