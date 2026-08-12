# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmChannel(models.Model):
    _inherit = 'crm.channel'

    whatsapp_provider = fields.Selection([
        ('cloud_api', 'Official WhatsApp Cloud API (Meta)'),
        ('baileys', 'Baileys - WhatsApp Web / QR Pairing (unofficial)'),
    ], string='WhatsApp Provider', default='cloud_api',
        help='Cloud API requires Meta Business verification and uses template '
             'messages outside the 24h window. Baileys pairs a normal WhatsApp '
             'number by QR code and has no template restriction, but is an '
             'unofficial protocol - use a dedicated number and expect it to '
             'occasionally require re-pairing.')

    # --- Bridge connection -------------------------------------------------
    baileys_base_url = fields.Char(
        string='Bridge Base URL',
        help='Base URL of the Baileys bridge microservice, e.g. '
             'https://wa-bridge.yourdomain.com (see bridge/README.md).')
    baileys_session_id = fields.Char(
        string='Session / Account',
        help='Unique session name the bridge uses to keep this WhatsApp '
             'pairing separate from any others it manages. Matches the '
             '"Account" field on the bridge side.')
    baileys_api_key = fields.Char(
        string='Bridge API Key',
        groups='crm_omnichannel_hub.group_omni_manager',
        help='Shared secret sent as the X-Bridge-Api-Key header on every '
             'call between Odoo and the bridge, both directions.')

    # --- Live status (written by the bridge via webhook) --------------------
    baileys_connection_state = fields.Selection([
        ('disconnected', 'Disconnected'),
        ('qr_pending', 'Waiting for QR Scan'),
        ('connected', 'Connected'),
    ], string='Connection Status', default='disconnected', readonly=True, copy=False)
    baileys_qr_image = fields.Binary(string='Pairing QR Code', readonly=True, copy=False, attachment=True)
    baileys_qr_updated = fields.Datetime(string='QR Last Updated', readonly=True, copy=False)
    baileys_last_seen = fields.Datetime(string='Last Heartbeat', readonly=True, copy=False)
    baileys_connected_number = fields.Char(string='Paired Number', readonly=True, copy=False)

    baileys_webhook_url = fields.Char(string='Inbound Webhook URL (give this to the bridge)',
                                       compute='_compute_baileys_webhook_url')

    @api.depends('baileys_session_id')
    def _compute_baileys_webhook_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.baileys_webhook_url = f'{base_url}/omni/webhook/whatsapp_baileys'

    # =====================================================================
    # ACTIONS (buttons on the channel form)
    # =====================================================================
    def action_baileys_start_pairing(self):
        """Ask the bridge to (re)start a session and generate a QR code."""
        self.ensure_one()
        self._baileys_require_config()
        data = self._baileys_call('POST', '/session/start', {
            'session_id': self.baileys_session_id,
            'webhook_url': self.baileys_webhook_url,
        })
        if data.get('state'):
            self.sudo().write({'baileys_connection_state': data['state']})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pairing requested'),
                'message': _('Check back in a few seconds - refresh the form to see the QR code, '
                              'or wait for the connection status to flip to Connected.'),
                'sticky': False,
            },
        }

    def action_baileys_refresh_status(self):
        self.ensure_one()
        self._baileys_require_config()
        data = self._baileys_call('GET', f'/session/{self.baileys_session_id}/status')
        vals = {}
        if data.get('state'):
            vals['baileys_connection_state'] = data['state']
        if data.get('phone_number'):
            vals['baileys_connected_number'] = data['phone_number']
        if vals:
            self.sudo().write(vals)

    def action_baileys_logout(self):
        self.ensure_one()
        self._baileys_require_config()
        self._baileys_call('POST', f'/session/{self.baileys_session_id}/logout')
        self.sudo().write({
            'baileys_connection_state': 'disconnected',
            'baileys_connected_number': False,
            'baileys_qr_image': False,
        })

    # =====================================================================
    # HELPERS
    # =====================================================================
    def _baileys_require_config(self):
        self.ensure_one()
        if not (self.baileys_base_url and self.baileys_session_id and self.baileys_api_key):
            raise UserError(_('Set Bridge Base URL, Session / Account and Bridge API Key first.'))

    def _baileys_call(self, method, path, json_payload=None):
        """Synchronous call to the bridge's small REST control API.
        Used for admin actions (start pairing / status / logout / send).
        Never raises to the UI on network failure - logs and returns {}."""
        self.ensure_one()
        import requests
        url = self.baileys_base_url.rstrip('/') + path
        headers = {'X-Bridge-Api-Key': self.baileys_api_key, 'Content-Type': 'application/json'}
        try:
            response = requests.request(method, url, json=json_payload, headers=headers, timeout=15)
        except requests.exceptions.RequestException:
            _logger.exception('Baileys bridge call failed: %s %s', method, url)
            self.message_post(body=_('Could not reach the Baileys bridge at %s. Is it running and reachable?') % url)
            return {}
        if response.status_code >= 400:
            _logger.error('Baileys bridge returned HTTP %s for %s %s: %s',
                           response.status_code, method, url, response.text[:500])
            self.message_post(body=_('Baileys bridge error (HTTP %s) on %s.') % (response.status_code, path))
            return {}
        try:
            return response.json()
        except ValueError:
            return {}
