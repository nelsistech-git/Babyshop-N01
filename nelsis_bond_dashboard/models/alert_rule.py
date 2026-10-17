# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
import logging

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .tools import ALERT_TYPES, SEVERITIES, eval_domain

_logger = logging.getLogger(__name__)
MAX_RECORDS = 2000
EVENT_TYPES = ('unauthorized_attempt',)


class BondDashboardAlertRule(models.Model):
    _name = 'bond.dashboard.alert.rule'
    _description = 'Bond Compliance Alert Rule'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    alert_type = fields.Selection(ALERT_TYPES, required=True)
    severity = fields.Selection(SEVERITIES, required=True, default='warning')
    model_name = fields.Char(
        string='Model',
        help='Model whose records are checked. Leave empty only for event rules (unauthorized attempt).')
    domain = fields.Char(default='[]', help='Records matching this domain raise an alert.')
    date_field = fields.Char(
        help='Optional date/datetime field. Records whose date is on or before today + lead days (including past dates) match.')
    lead_days = fields.Integer(string='Lead days', default=30)
    ratio_numerator_field = fields.Char(string='Ratio numerator field')
    ratio_denominator_field = fields.Char(string='Ratio denominator field')
    threshold_percent = fields.Float(string='Threshold %', default=80.0,
                                     help='Used with the ratio fields: matches when numerator / denominator >= threshold.')
    user_ids = fields.Many2many('res.users', 'bond_dashboard_rule_user_rel', 'rule_id', 'user_id', string='Notify users')
    group_ids = fields.Many2many('res.groups', 'bond_dashboard_rule_group_rel', 'rule_id', 'group_id', string='Notify groups')
    notify_message = fields.Boolean(string='Odoo notification / email', default=True,
                                    help='Delivered according to each user\'s notification preference (Inbox or Email).')
    notify_activity = fields.Boolean(string='Schedule activity', default=True)
    message_template = fields.Char(
        default='{record} needs attention ({rule}). Deadline: {deadline}',
        help='Placeholders: {record}, {rule}, {deadline}')
    last_run = fields.Datetime(readonly=True)
    last_match_count = fields.Integer(readonly=True)
    last_error = fields.Text(readonly=True)

    @api.constrains('alert_type', 'model_name', 'date_field', 'lead_days', 'ratio_numerator_field', 'ratio_denominator_field')
    def _check_configuration(self):
        for rule in self:
            if rule.alert_type not in EVENT_TYPES and not rule.model_name:
                raise ValidationError(_('"%s": a model is required for this alert type.', rule.name))
            if rule.date_field and not rule.model_name:
                raise ValidationError(_('"%s": a date field needs a model.', rule.name))
            if rule.lead_days < 0:
                raise ValidationError(_('Lead days cannot be negative.'))
            if bool(rule.ratio_numerator_field) != bool(rule.ratio_denominator_field):
                raise ValidationError(_('Set both ratio fields, or neither.'))

    # ------------------------------------------------------------------
    def _get_recipients(self):
        self.ensure_one()
        users = self.user_ids
        if self.group_ids:
            users |= self.env['res.users'].sudo().search([('groups_id', 'in', self.group_ids.ids)])
        return users.filtered(lambda u: u.active and not u.share)

    def _find_matches(self):
        """Records (sudo) that currently require an alert."""
        self.ensure_one()
        if self.model_name not in self.env:
            raise UserError(_('Model %s is not installed.', self.model_name))
        Model = self.env[self.model_name].sudo()
        domain = eval_domain(self.env, self.domain)
        if self.date_field:
            field = Model._fields.get(self.date_field)
            if field is None or field.type not in ('date', 'datetime'):
                raise UserError(_('"%(field)s" is not a date field on %(model)s.', field=self.date_field, model=self.model_name))
            today = fields.Date.context_today(self)
            limit = today + relativedelta(days=self.lead_days + 1)
            domain += [(self.date_field, '!=', False), (self.date_field, '<', limit)]
        records = Model.search(domain, limit=MAX_RECORDS)
        if self.ratio_numerator_field:
            num, den = self.ratio_numerator_field, self.ratio_denominator_field
            for fname in (num, den):
                if fname not in Model._fields:
                    raise UserError(_('Field "%(field)s" does not exist on %(model)s.', field=fname, model=self.model_name))
            records = records.filtered(lambda r: r[den] and (r[num] / r[den] * 100.0) >= self.threshold_percent)
        return records

    def _run(self):
        """Evaluate this rule. Returns the alerts created in this run."""
        self.ensure_one()
        Alert = self.env['bond.dashboard.alert'].sudo()
        created = Alert
        if not self.model_name:
            return created
        try:
            with self.env.cr.savepoint():
                matches = self._find_matches()
                open_alerts = Alert.search([
                    ('rule_id', '=', self.id), ('state', '!=', 'resolved'), ('res_model', '=', self.model_name)])
                existing = set(open_alerts.mapped('res_id'))
                match_ids = set(matches.ids)
                for record in matches:
                    if record.id not in existing:  # never raise the same alert twice
                        created |= Alert._create_from_rule(self, record)
                open_alerts.filtered(lambda a: a.res_id not in match_ids)._auto_resolve()
                self.sudo().write({'last_run': fields.Datetime.now(), 'last_match_count': len(matches), 'last_error': False})
        except Exception as exc:
            _logger.warning('Alert rule "%s" failed: %s', self.name, exc)
            created = Alert
            self.sudo().write({'last_run': fields.Datetime.now(), 'last_match_count': 0, 'last_error': str(exc)})
            return created
        created._notify()
        return created

    @api.model
    def _cron_run_rules(self):
        for rule in self.sudo().search([('active', '=', True)]):
            rule._run()
        return True

    # ------------------------------------------------------------------
    def action_run_now(self):
        self.ensure_one()
        created = self._run()
        if self.last_error:
            return self._notification(_('Rule failed'), self.last_error, 'danger', True)
        return self._notification(
            _('Rule evaluated'),
            _('%(matches)s matching record(s), %(new)s new alert(s).', matches=self.last_match_count, new=len(created)),
            'success', False)

    def action_preview_matches(self):
        self.ensure_one()
        try:
            records = self._find_matches()
        except Exception as exc:
            raise UserError(_('Rule cannot be evaluated: %s', exc))
        if not records:
            return self._notification(_('Preview'), _('No record matches right now.'), 'info', False)
        return {
            'type': 'ir.actions.act_window', 'name': self.name, 'res_model': self.model_name,
            'views': [[False, 'list'], [False, 'form']], 'domain': [('id', 'in', records.ids)],
        }

    @staticmethod
    def _notification(title, message, kind, sticky):
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': title, 'message': message, 'type': kind, 'sticky': sticky}}
