# -*- coding: utf-8 -*-
"""Multi-channel alert delivery (SRS feature 12), siren hook and escalation (feature 6).

cctv.alert.channel   - where alerts go: Telegram, WhatsApp Cloud API, any HTTP SMS
                       gateway, a generic webhook, or a siren/relay HTTP endpoint.
cctv.alert.delivery  - one row per (alert, channel, recipient): what was sent,
                       when, whether it worked. Sending is done by a cron job
                       (triggered immediately on alert creation) so a slow SMS
                       gateway can never block the AI webhook.

Escalation: channels with escalation_level >= 1 only fire if the alert is
still 'new' (nobody acknowledged it) after that channel's delay.
"""
import base64
import json
import logging
import urllib.parse
from datetime import timedelta

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

SEVERITY_RANK = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
HTTP_TIMEOUT = 8
MAX_ATTEMPTS = 3


class CctvAlertChannel(models.Model):
    _name = 'cctv.alert.channel'
    _description = 'Alert Notification Channel'
    _order = 'escalation_level, sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    channel_type = fields.Selection([
        ('telegram', 'Telegram Bot'),
        ('whatsapp', 'WhatsApp Cloud API'),
        ('sms', 'SMS (HTTP gateway)'),
        ('webhook', 'Generic Webhook'),
        ('siren', 'Siren / Relay (HTTP)'),
    ], required=True, default='telegram')

    # --- routing rules
    min_severity = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], default='high', required=True, string='Minimum Severity')
    scope = fields.Selection([
        ('all', 'All alerts'),
        ('security', 'Security / AI events (not camera-offline)'),
        ('emergency', 'Fire / smoke emergencies only'),
    ], default='all', required=True)
    office_ids = fields.Many2many('cctv.office', string='Only for Sites',
                                  help='Leave empty to apply to every site.')
    escalation_level = fields.Integer(
        default=0, help='0 = notify immediately. 1, 2, 3... = only notify if the alert is still '
                        'unacknowledged after "Escalate After" minutes (escalation to senior staff).')
    escalate_after_minutes = fields.Integer(default=10)
    cooldown_minutes = fields.Integer(
        default=5, help='Do not re-notify this channel about the same camera and alert type '
                        'within this many minutes (prevents message floods).')

    # --- connection
    recipients = fields.Text(
        help='One per line. Telegram: chat id. WhatsApp/SMS: phone number with country code '
             '(e.g. 8801XXXXXXXXX). Not used for webhook/siren.')
    endpoint_url = fields.Char(
        string='Endpoint URL',
        help='Telegram: leave empty (uses api.telegram.org). WhatsApp: leave empty to use the '
             'Graph API with the Phone Number ID below. SMS/webhook/siren: the full URL. '
             'In SMS URLs/bodies you can use {to} {message} {alert} {severity} {camera} {branch} {time}.')
    auth_token = fields.Char(string='Token / API Key', groups='cctv_management.group_cctv_security_director',
                             help='Telegram bot token, WhatsApp permanent access token, or the gateway API key.')
    provider_ref = fields.Char(string='WhatsApp Phone Number ID')
    whatsapp_template = fields.Char(
        string='WhatsApp Template Name',
        help='Required by Meta for business-initiated messages outside the 24h window. The template '
             'must have 5 body variables: {{1}} alert, {{2}} branch, {{3}} camera, {{4}} time, {{5}} severity. '
             'Leave empty to send free-form text (only delivered if the recipient messaged you in the last 24h).')
    whatsapp_lang = fields.Char(default='en')
    http_method = fields.Selection([('POST', 'POST'), ('GET', 'GET')], default='POST')
    auth_header = fields.Char(
        string='Auth Header Name', default='Authorization',
        help='Header that carries the token for SMS/webhook/siren (value sent as "Bearer <token>").')
    body_format = fields.Selection([('json', 'JSON'), ('form', 'Form-encoded')], default='json')
    body_template = fields.Text(
        string='Body Template (JSON)',
        help='JSON object; string values may use {to} {message} {alert} {severity} {camera} {branch} {time} '
             '{status} {link}. Example for an SMS gateway: {"to": "{to}", "text": "{message}"}. '
             'Empty = a default JSON describing the alert.')
    delivery_ids = fields.One2many('cctv.alert.delivery', 'channel_id')

    def action_send_test(self):
        """Send a harmless test message through this channel."""
        self.ensure_one()
        alert = self.env['cctv.alert'].create({
            'name': 'TEST - alert channel check (%s)' % self.name,
            'alert_type': 'other', 'severity': 'low', 'state': 'ignored', 'notes': 'Test message, please ignore.',
        })
        deliveries = self._make_deliveries(alert)
        deliveries._send()
        failed = deliveries.filtered(lambda d: d.state == 'failed')
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'title': 'Test sent' if not failed else 'Test failed',
            'message': ('Delivered to %d recipient(s).' % len(deliveries)) if not failed else
                       (failed[0].error or 'Unknown error'),
            'type': 'success' if not failed else 'danger', 'sticky': bool(failed)}}

    # ---------------------------------------------------------------- routing
    def _matches(self, alert):
        self.ensure_one()
        if SEVERITY_RANK.get(alert.severity, 2) < SEVERITY_RANK[self.min_severity]:
            return False
        if self.office_ids and alert.office_id not in self.office_ids:
            return False
        if self.scope == 'emergency' and alert.alert_type not in ('fire', 'smoke'):
            return False
        if self.scope == 'security' and alert.alert_type == 'camera_offline':
            return False
        return True

    def _recipient_list(self):
        self.ensure_one()
        if self.channel_type in ('webhook', 'siren'):
            return ['']
        return [r.strip() for r in (self.recipients or '').splitlines() if r.strip()]

    def _in_cooldown(self, alert):
        self.ensure_one()
        if not self.cooldown_minutes or not alert.camera_id:
            return False
        since = fields.Datetime.now() - timedelta(minutes=self.cooldown_minutes)
        return bool(self.env['cctv.alert.delivery'].sudo().search_count([
            ('channel_id', '=', self.id), ('alert_id.camera_id', '=', alert.camera_id.id),
            ('alert_id.alert_type', '=', alert.alert_type), ('alert_id', '!=', alert.id),
            ('create_date', '>=', since), ('state', 'in', ('sent', 'pending')),
        ]))

    def _make_deliveries(self, alert, check_cooldown=False):
        Delivery = self.env['cctv.alert.delivery'].sudo()
        deliveries = Delivery
        for channel in self:
            if check_cooldown and channel._in_cooldown(alert):
                continue
            for rcpt in channel._recipient_list():
                deliveries |= Delivery.create({
                    'alert_id': alert.id, 'channel_id': channel.id, 'recipient': rcpt,
                    'escalation_level': channel.escalation_level,
                })
        return deliveries

    # ---------------------------------------------------------------- sending
    @staticmethod
    def _render(obj, ctx):
        """Substitute {placeholders} in every string of a JSON-like object."""
        if isinstance(obj, str):
            out = obj
            for k, v in ctx.items():
                out = out.replace('{%s}' % k, str(v))
            return out
        if isinstance(obj, dict):
            return {k: CctvAlertChannel._render(v, ctx) for k, v in obj.items()}
        if isinstance(obj, list):
            return [CctvAlertChannel._render(v, ctx) for v in obj]
        return obj

    def _send_one(self, delivery, ctx):
        """Perform one HTTP call. Returns response text. Raises on failure."""
        self.ensure_one()
        token = self.sudo().auth_token or ''
        ctype = self.channel_type
        to = delivery.recipient

        if ctype == 'telegram':
            base = 'https://api.telegram.org/bot%s' % token
            snap = delivery.alert_id.event_id.snapshot
            if snap:
                resp = requests.post(
                    self.endpoint_url or base + '/sendPhoto',
                    data={'chat_id': to, 'caption': ctx['message'][:1000]},
                    files={'photo': ('snapshot.jpg', base64.b64decode(snap), 'image/jpeg')},
                    timeout=HTTP_TIMEOUT)
            else:
                resp = requests.post(self.endpoint_url or base + '/sendMessage',
                                     json={'chat_id': to, 'text': ctx['message']}, timeout=HTTP_TIMEOUT)

        elif ctype == 'whatsapp':
            url = self.endpoint_url or 'https://graph.facebook.com/v19.0/%s/messages' % (self.provider_ref or '')
            if self.whatsapp_template:
                payload = {'messaging_product': 'whatsapp', 'to': to, 'type': 'template', 'template': {
                    'name': self.whatsapp_template, 'language': {'code': self.whatsapp_lang or 'en'},
                    'components': [{'type': 'body', 'parameters': [
                        {'type': 'text', 'text': ctx[k]} for k in ('alert', 'branch', 'camera', 'time', 'severity')
                    ]}]}}
            else:
                payload = {'messaging_product': 'whatsapp', 'to': to, 'type': 'text',
                           'text': {'body': ctx['message']}}
            resp = requests.post(url, json=payload, timeout=HTTP_TIMEOUT,
                                 headers={'Authorization': 'Bearer %s' % token})

        else:   # sms / webhook / siren : generic HTTP call
            if not self.endpoint_url:
                raise ValueError('Endpoint URL is not configured on channel "%s".' % self.name)
            headers = {}
            if token and self.auth_header:
                headers[self.auth_header] = 'Bearer %s' % token if self.auth_header.lower() == 'authorization' \
                    else token
            if self.http_method == 'GET':
                quoted = {k: urllib.parse.quote(str(v), safe='') for k, v in ctx.items()}
                url = self.endpoint_url
                for k, v in quoted.items():
                    url = url.replace('{%s}' % k, v)
                resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            else:
                url = self.endpoint_url
                for k in ('to',):
                    url = url.replace('{%s}' % k, urllib.parse.quote(str(ctx[k]), safe=''))
                if self.body_template:
                    body = self._render(json.loads(self.body_template), ctx)
                else:
                    body = {k: ctx[k] for k in ('alert', 'severity', 'camera', 'branch', 'time', 'status',
                                                'link', 'message')}
                    body['alert_id'] = delivery.alert_id.id
                    body['alert_type'] = delivery.alert_id.alert_type
                if self.body_format == 'form':
                    resp = requests.post(url, data=body, headers=headers, timeout=HTTP_TIMEOUT)
                else:
                    resp = requests.post(url, json=body, headers=headers, timeout=HTTP_TIMEOUT)

        resp.raise_for_status()
        return (resp.text or '')[:500]


class CctvAlertDelivery(models.Model):
    _name = 'cctv.alert.delivery'
    _description = 'Alert Delivery Log'
    _order = 'create_date desc, id desc'

    alert_id = fields.Many2one('cctv.alert', required=True, ondelete='cascade', index=True)
    channel_id = fields.Many2one('cctv.alert.channel', required=True, ondelete='cascade')
    channel_type = fields.Selection(related='channel_id.channel_type', store=True)
    recipient = fields.Char()
    escalation_level = fields.Integer(default=0)
    state = fields.Selection([('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed')],
                             default='pending', index=True)
    attempts = fields.Integer(default=0)
    sent_at = fields.Datetime()
    response = fields.Char()
    error = fields.Text()

    def _build_context(self):
        self.ensure_one()
        alert = self.alert_id
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        link = '%s/web#id=%s&model=cctv.alert&view_type=form' % (base, alert.id)
        status = {'new': 'NEW - not acknowledged', 'acknowledged': 'Acknowledged',
                  'resolved': 'Resolved', 'ignored': 'Ignored'}.get(alert.state, alert.state)
        when = alert.event_id.event_time or alert.create_date
        ctx = {
            'to': self.recipient or '', 'alert': alert.name or '', 'severity': (alert.severity or '').upper(),
            'camera': alert.camera_id.display_name or '-', 'branch': alert.office_id.name or '-',
            'time': fields.Datetime.to_string(when) + ' UTC' if when else '', 'status': status, 'link': link,
        }
        prefix = 'ESCALATION L%d - ' % self.escalation_level if self.escalation_level else ''
        ctx['message'] = (
            '%s[%s] %s\nBranch: %s\nCamera: %s\nTime: %s\nStatus: %s\nOpen: %s'
            % (prefix, ctx['severity'], ctx['alert'], ctx['branch'], ctx['camera'], ctx['time'],
               ctx['status'], link))
        return ctx

    def _send(self):
        for rec in self.sudo():
            rec.attempts += 1
            try:
                ctx = rec._build_context()
                resp = rec.channel_id._send_one(rec, ctx)
                rec.write({'state': 'sent', 'sent_at': fields.Datetime.now(), 'response': resp, 'error': False})
            except Exception as exc:   # noqa: BLE001 - any transport/config error is logged on the row
                _logger.warning('Alert delivery %s failed: %s', rec.id, exc)
                rec.write({'state': 'failed' if rec.attempts >= MAX_ATTEMPTS else 'pending',
                           'error': str(exc)[:1000]})

    @api.model
    def cron_send_pending(self):
        pending = self.search([('state', '=', 'pending'), ('attempts', '<', MAX_ATTEMPTS)], limit=200)
        pending._send()
        return len(pending)

    @api.model
    def cron_escalate_alerts(self):
        """Alerts nobody acknowledged get pushed to the next escalation level."""
        Channel = self.env['cctv.alert.channel'].sudo()
        Alert = self.env['cctv.alert'].sudo()
        now = fields.Datetime.now()
        levels = sorted({c.escalation_level for c in Channel.search([('escalation_level', '>', 0)])})
        candidates = {lvl: Alert.search([('state', '=', 'new'), ('escalation_level', '<', lvl)]).ids
                      for lvl in levels}   # snapshot first, so an alert is not processed twice in one run
        for lvl in levels:
            channels = Channel.search([('escalation_level', '=', lvl)])
            for alert in Alert.browse(candidates[lvl]):
                age = (now - alert.create_date).total_seconds() / 60.0
                due = channels.filtered(lambda c: age >= c.escalate_after_minutes and c._matches(alert))
                if due:
                    due._make_deliveries(alert)
                    alert.write({'escalation_level': lvl, 'last_escalated_at': now})
                    alert.message_post(body='Not acknowledged after %d min - escalated to level %d.' % (age, lvl))
        self.cron_send_pending()
