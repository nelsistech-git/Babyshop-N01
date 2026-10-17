# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import models, _
from odoo.exceptions import AccessError

from .constants import TECH_FIELDS


class NelsisLcGuardMixin(models.AbstractModel):
    """Server-side permission helpers shared by all LC models.

    Workflow methods call ``_assert_group`` first, so hiding a button in the
    view is never the only protection.  Privileged writes (state changes,
    amendment application) run through ``sudo()`` which is detected with
    ``env.su``; a client cannot spoof that through RPC context.
    """
    _name = 'nelsis.lc.guard.mixin'
    _description = 'Nelsis LC Guard Mixin'

    def _assert_group(self, xmlid):
        if self.env.su:
            return
        if not self.env.user.has_group(xmlid):
            raise AccessError(_('You are not allowed to perform this action. Required role: %s',
                                self.env.ref(xmlid).full_name))
        self.check_access_rights('write')
        self.check_access_rule('write')

    @staticmethod
    def _business_vals(vals):
        return set(vals) - TECH_FIELDS

    def _open_reason_wizard(self, action_type, title):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'nelsis.lc.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_action_type': action_type,
            },
        }
