# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

MANAGER_GROUP = 'nelsis_bond_license.group_bond_license_manager'


class BondLifecycleMixin(models.AbstractModel):
    """Audit trail, controlled status transitions and delete protection."""
    _name = 'bond.warehouse.lifecycle.mixin'
    _description = 'Bond Warehouse Lifecycle and Audit Mixin'

    # action_code -> (set of allowed source states, target state)
    _bond_status_transitions = {}
    _bond_deletable_states = ('draft',)

    history_ids = fields.One2many('bond.warehouse.history', 'res_id', string='Audit Trail',
                                  readonly=True)

    # ------------------------------------------------------------------ audit
    def _log_history(self, event, note='', from_state=False, to_state=False, event_date=None):
        vals_list = []
        for rec in self:
            vals_list.append({
                'res_model': rec._name,
                'res_id': rec.id,
                'company_id': rec.company_id.id or self.env.company.id,
                'event': event,
                'from_state': from_state or False,
                'to_state': to_state or False,
                'note': note or False,
                'event_date': event_date or fields.Date.context_today(rec),
                'user_id': self.env.user.id,
            })
        return self.env['bond.warehouse.history'].sudo().create(vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._log_history('create', to_state=rec.state)
        return records

    def unlink(self):
        for rec in self:
            if rec.state not in self._bond_deletable_states:
                raise UserError(_(
                    "'%(name)s' is in state '%(state)s' and cannot be deleted. "
                    "Use the cancel/release/reverse action to keep the history.",
                    name=rec.display_name, state=rec.state))
        model, ids = self._name, self.ids
        res = super().unlink()
        self.env['bond.warehouse.history'].sudo().with_context(bond_history_cleanup=True).search(
            [('res_model', '=', model), ('res_id', 'in', ids)]).unlink()
        return res

    # ---------------------------------------------------------------- status
    def _bond_require_manager(self):
        if not self.env.user.has_group(MANAGER_GROUP):
            raise AccessError(_('Only Bond License Managers can perform this action.'))

    def _bond_before_transition(self, action_code, target):
        """Hook: validate and optionally change the target state."""
        return target

    def _bond_apply_status(self, action_code, reason, change_date=None):
        self.ensure_one()
        transition = self._bond_status_transitions.get(action_code)
        if not transition:
            raise UserError(_("Unknown action '%s'.", action_code))
        allowed, target = transition
        if self.state not in allowed:
            raise UserError(_(
                "Action '%(action)s' is not allowed for '%(name)s' in state '%(state)s'.",
                action=action_code, name=self.display_name, state=self.state))
        target = self._bond_before_transition(action_code, target) or target
        old_state = self.state
        self.with_context(bond_status_change=True).write({'state': target})
        self._log_history(action_code, reason, old_state, target, change_date)
        return True

    def _bond_open_wizard(self, action_code, label):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': label,
            'res_model': 'bond.warehouse.status.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_action_code': action_code,
                'default_action_label': label,
            },
        }


class BondExpiryMixin(models.AbstractModel):
    """Automatic expiry and configurable reminders."""
    _name = 'bond.warehouse.expiry.mixin'
    _description = 'Bond Warehouse Expiry and Reminder Mixin'

    _bond_expiry_field = 'expiry_date'
    _bond_active_states = ('active',)

    last_reminder_days = fields.Integer(copy=False, readonly=True,
                                        help='Last reminder threshold (days) already sent.')

    def write(self, vals):
        if self._bond_expiry_field in vals and 'last_reminder_days' not in vals:
            vals = dict(vals, last_reminder_days=0)
        return super().write(vals)

    def _bond_responsible_user(self):
        self.ensure_one()
        return self.create_uid

    def _bond_mark_expired(self):
        self.ensure_one()
        old_state = self.state
        self.with_context(bond_status_change=True).write({'state': 'expired'})
        self._log_history('expired', _('Automatically expired on %s.', fields.Date.context_today(self)),
                          old_state, 'expired')

    @api.model
    def _cron_check_expiry(self):
        today = fields.Date.context_today(self)
        expired = self.search([('state', 'in', list(self._bond_active_states)),
                               (self._bond_expiry_field, '<', today)])
        for rec in expired:
            rec._bond_mark_expired()
        self._cron_send_expiry_reminders()

    @api.model
    def _cron_send_expiry_reminders(self):
        today = fields.Date.context_today(self)
        records = self.search([('state', 'in', list(self._bond_active_states)),
                               (self._bond_expiry_field, '>=', today)])
        for rec in records:
            days_left = (rec[self._bond_expiry_field] - today).days
            candidates = [t for t in rec.company_id._bond_reminder_thresholds() if t >= days_left]
            if not candidates:
                continue
            threshold = min(candidates)
            if rec.last_reminder_days and threshold >= rec.last_reminder_days:
                continue
            user = rec._bond_responsible_user()
            if user:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=rec[self._bond_expiry_field],
                    summary=_('%(name)s expires in %(days)s day(s)', name=rec.display_name, days=days_left),
                    user_id=user.id)
            rec.write({'last_reminder_days': threshold})


class BondRuleMixin(models.AbstractModel):
    """Regulatory basis and verification record. No legal value is hard-coded."""
    _name = 'bond.warehouse.rule.mixin'
    _description = 'Bond Warehouse Regulatory Basis Mixin'

    _RULE_CONTENT_FIELDS = ('rule_reference', 'rule_source_url', 'rule_published_date',
                            'rule_effective_date', 'rule_applicability', 'rule_required_document')

    rule_reference = fields.Char(string='Official Rule / SRO Reference', copy=False)
    rule_source_url = fields.Char(string='Source URL', copy=False)
    rule_published_date = fields.Date(string='Rule Publication Date', copy=False)
    rule_effective_date = fields.Date(string='Rule Effective Date', copy=False)
    rule_applicability = fields.Text(string='Applicability to Factory / License Category', copy=False)
    rule_required_document = fields.Text(string='Required Document / Validation', copy=False)
    rule_verification_status = fields.Selection(
        [('unverified', 'Unverified'), ('needs_review', 'Needs Review'), ('verified', 'Verified')],
        default='unverified', required=True, copy=False)
    rule_verified_by_id = fields.Many2one('res.users', string='Verified By', copy=False, readonly=True)
    rule_verified_date = fields.Date(string='Verified On', copy=False, readonly=True)
    rule_reviewer_note = fields.Text(string='Reviewer Note', copy=False)

    def write(self, vals):
        if any(f in vals for f in self._RULE_CONTENT_FIELDS) and 'rule_verification_status' not in vals:
            vals = dict(vals, rule_verification_status='unverified',
                        rule_verified_by_id=False, rule_verified_date=False)
        return super().write(vals)

    def _bond_check_rule_verified(self):
        for rec in self:
            if rec.company_id.bond_require_verified_rule and rec.rule_verification_status != 'verified':
                raise UserError(_(
                    "The regulatory basis of '%s' has not been verified. Record the official rule "
                    "reference and have an authorised reviewer verify it before activation.",
                    rec.display_name))

    def action_verify_rule(self):
        self._bond_require_manager()
        for rec in self:
            if not (rec.rule_reference and rec.rule_source_url and rec.rule_applicability):
                raise UserError(_('Rule reference, source URL and applicability must be recorded before verification.'))
            rec.write({'rule_verification_status': 'verified',
                       'rule_verified_by_id': self.env.user.id,
                       'rule_verified_date': fields.Date.context_today(rec)})
            rec._log_history('rule_verified', rec.rule_reference)
        return True

    def action_flag_rule_review(self):
        self._bond_require_manager()
        for rec in self:
            rec.write({'rule_verification_status': 'needs_review',
                       'rule_verified_by_id': False, 'rule_verified_date': False})
            rec._log_history('rule_needs_review', rec.rule_reviewer_note)
        return True
