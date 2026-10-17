# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import fields, models, _
from odoo.exceptions import UserError

from .constants import LC_STATES


class NelsisLcLog(models.Model):
    """Append-only approval and audit trail.  Created only by the workflow code."""
    _name = 'nelsis.lc.log'
    _description = 'LC Approval and Audit Log'
    _order = 'date desc, id desc'

    lc_id = fields.Many2one('nelsis.lc', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='lc_id.company_id', store=True, index=True)
    date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.uid, readonly=True)
    event = fields.Char(required=True, readonly=True)
    from_state = fields.Selection(LC_STATES, readonly=True)
    to_state = fields.Selection(LC_STATES, readonly=True)
    note = fields.Text(readonly=True)

    def write(self, vals):
        raise UserError(_('Audit log entries cannot be modified.'))

    def unlink(self):
        raise UserError(_('Audit log entries cannot be deleted.'))
