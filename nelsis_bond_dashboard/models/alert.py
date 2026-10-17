# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
import logging
from datetime import datetime

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html_escape

from .tools import ALERT_TYPES, SEVERITIES

_logger = logging.getLogger(__name__)
TODO = 'mail.mail_activity_data_todo'


class BondDashboardAlert(models.Model):
    """Alert log. It points at source records; it never copies stock data."""
    _name = 'bond.dashboard.alert'
    _description = 'Bond Compliance Alert'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(required=True, readonly=True)
    rule_id = fields.Many2one('bond.dashboard.alert.rule', string='Rule', ondelete='set null', readonly=True)
    alert_type = fields.Selection(ALERT_TYPES, required=True, readonly=True, index=True)
    severity = fields.Selection(SEVERITIES, required=True, default='warning', readonly=True)
    state = fields.Selection([
        ('open', 'Open'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved'),
    ], default='open', required=True, tracking=True, index=True, readonly=True)
    res_model = fields.Char(string='Source model', readonly=True, index=True)
    res_id = fields.Integer(string='Source record ID', readonly=True, index=True)
    res_name = fields.Char(string='Source record', readonly=True)
    message = fields.Text(readonly=True)
    deadline = fields.Date(readonly=True)
    recipient_user_ids = fields.Many2many(
        'res.users', 'bond_dashboard_alert_user_rel', 'alert_id', 'user_id', string='Recipients', readonly=True)
    acknowledged_by_id = fields.Many2one('res.users', readonly=True)
    acknowledged_date = fields.Datetime(readonly=True)
    resolved_date = fields.Datetime(readonly=True)
    auto_resolved = fields.Boolean(readonly=True)
    resolution_note = fields.Text(tracking=True)

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------
    @api.model
    def _create_from_rule(self, rule, record):
        deadline = False
        if rule.date_field:
            value = record[rule.date_field]
            deadline = value.date() if isinstance(value, datetime) else value
        text = (rule.message_template or '{record} needs attention ({rule}).')
        text = (text.replace('{record}', record.display_name or '')
                .replace('{rule}', rule.name or '')
                .replace('{deadline}', fields.Date.to_string(deadline) if deadline else '-'))
        return self.sudo().create({
            'name': '%s: %s' % (rule.name, record.display_name),
            'rule_id': rule.id, 'alert_type': rule.alert_type, 'severity': rule.severity,
            'res_model': record._name, 'res_id': record.id, 'res_name': record.display_name,
            'message': text, 'deadline': deadline,
            'recipient_user_ids': [(6, 0, rule._get_recipients().ids)],
        })

    @api.model
    def log_unauthorized_attempt(self, res_model, res_id=0, reason='', user_id=None):
        """Public API for other Nelsis modules: log a blocked transaction attempt.

        Call as ``env['bond.dashboard.alert'].log_unauthorized_attempt(model, id, reason)``.
        """
        user = self.env['res.users'].sudo().browse(user_id or self.env.uid)
        rule = self.env['bond.dashboard.alert.rule'].sudo().search(
            [('alert_type', '=', 'unauthorized_attempt'), ('active', '=', True)], limit=1)
        if rule:
            recipients = rule._get_recipients()
        else:
            group_ids = [
                self.env.ref('nelsis_bond_dashboard.group_bond_dash_auditor').id,
                self.env.ref('nelsis_bond_dashboard.group_bond_dash_bond_manager').id,
            ]
            recipients = self.env['res.users'].sudo().search([('groups_id', 'in', group_ids)])
        alert = self.sudo().create({
            'name': _('Unauthorized transaction attempt by %s', user.name),
            'rule_id': rule.id or False, 'alert_type': 'unauthorized_attempt', 'severity': 'critical',
            'res_model': res_model, 'res_id': res_id or 0,
            'message': reason or _('A transaction was blocked because the user was not authorised.'),
            'deadline': fields.Date.context_today(self),
            'recipient_user_ids': [(6, 0, recipients.ids)],
        })
        alert._notify()
        return alert.id

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _notify(self):
        for alert in self:
            try:
                with self.env.cr.savepoint():
                    alert._send_notifications()
            except Exception:
                _logger.exception('Could not notify for alert %s', alert.id)

    def _send_notifications(self):
        self.ensure_one()
        users = self.recipient_user_ids
        if not users:
            return
        rule = self.rule_id
        if (rule.notify_message if rule else True):
            self.message_notify(
                partner_ids=users.partner_id.ids,
                subject=self.name,
                body=Markup('<p>%s</p>') % (self.message or self.name),
                email_layout_xmlid='mail.mail_notification_light')
        if (rule.notify_activity if rule else True):
            today = fields.Date.context_today(self)
            for user in users:
                try:
                    with self.env.cr.savepoint():
                        self.activity_schedule(
                            TODO, date_deadline=today, summary=self.name,
                            note=html_escape(self.message or ''), user_id=user.id)
                except Exception as exc:
                    _logger.warning('Activity for %s on alert %s skipped: %s', user.login, self.id, exc)

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_acknowledge(self):
        for alert in self.filtered(lambda a: a.state == 'open'):
            alert.write({'state': 'acknowledged', 'acknowledged_by_id': self.env.uid,
                         'acknowledged_date': fields.Datetime.now()})
            alert.activity_feedback([TODO], feedback=_('Acknowledged'))
        return True

    def action_resolve(self):
        for alert in self:
            if alert.state == 'resolved':
                continue
            if not (alert.resolution_note or '').strip():
                raise UserError(_('Enter a resolution note before resolving "%s".', alert.name))
            alert.write({'state': 'resolved', 'resolved_date': fields.Datetime.now()})
            alert.sudo().activity_unlink([TODO])
        return True

    def _auto_resolve(self):
        """The source condition no longer holds: close the alert, keep the record."""
        if not self:
            return
        self.sudo().write({
            'state': 'resolved', 'resolved_date': fields.Datetime.now(), 'auto_resolved': True,
            'resolution_note': _('Closed automatically: the condition no longer matches.'),
        })
        self.sudo().activity_unlink([TODO])

    def action_open_source(self):
        self.ensure_one()
        if not (self.res_model and self.res_id) or self.res_model not in self.env:
            raise UserError(_('This alert has no source record.'))
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            raise UserError(_('The source record no longer exists.'))
        record.check_access_rights('read')
        record.check_access_rule('read')
        return {'type': 'ir.actions.act_window', 'res_model': self.res_model, 'res_id': self.res_id,
                'views': [[False, 'form']], 'target': 'current'}

    @api.ondelete(at_uninstall=False)
    def _unlink_except_unresolved(self):
        if any(alert.state != 'resolved' for alert in self):
            raise UserError(_('Only resolved alerts can be deleted; open alerts are part of the audit trail.'))
