# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CrmChannel(models.Model):
    _inherit = 'crm.channel'

    connect_status_label = fields.Char(string='Status', compute='_compute_connect_status')
    connect_status_color = fields.Selection([
        ('success', 'Connected'), ('warning', 'Pending'), ('danger', 'Disconnected'), ('muted', 'Not configured'),
    ], compute='_compute_connect_status')

    @api.depends('code', 'whatsapp_provider', 'baileys_connection_state',
                 'meta_page_id', 'page_access_token', 'ami_host', 'ami_username', 'ami_secret')
    def _compute_connect_status(self):
        for rec in self:
            if rec.code == 'whatsapp' and rec.whatsapp_provider == 'baileys':
                state = rec.baileys_connection_state
                rec.connect_status_label = {
                    'connected': _('Connected'),
                    'qr_pending': _('Waiting for QR scan'),
                    'disconnected': _('Disconnected'),
                }.get(state, _('Not configured'))
                rec.connect_status_color = {
                    'connected': 'success', 'qr_pending': 'warning', 'disconnected': 'danger',
                }.get(state, 'muted')
            elif rec.code in ('facebook', 'instagram'):
                if rec.meta_page_id and rec.page_access_token:
                    rec.connect_status_label = _('Connected')
                    rec.connect_status_color = 'success'
                else:
                    rec.connect_status_label = _('Not connected')
                    rec.connect_status_color = 'muted'
            elif rec.code == 'call':
                if rec.ami_host and rec.ami_username and rec.ami_secret:
                    rec.connect_status_label = _('Configured (click Test Connection to verify)')
                    rec.connect_status_color = 'warning'
                else:
                    rec.connect_status_label = _('Not connected')
                    rec.connect_status_color = 'muted'
            else:
                rec.connect_status_label = _('Not configured')
                rec.connect_status_color = 'muted'

    def action_test_connection(self):
        """Unified 'does this actually work right now' check, surfaced as a
        sticky notification with the real cause instead of a generic failure."""
        self.ensure_one()
        if self.code == 'whatsapp' and self.whatsapp_provider == 'baileys':
            return self._test_baileys_connection()
        if self.code in ('facebook', 'instagram'):
            return self._test_meta_page_connection()
        if self.code == 'call':
            return self._test_voip_connection()
        return self._connect_notify(False, _('Nothing to test for this channel type.'))

    def _test_baileys_connection(self):
        self.ensure_one()
        if not (self.baileys_base_url and self.baileys_session_id and self.baileys_api_key):
            return self._connect_notify(False, _('Bridge URL, Session ID and API Key must all be set.'))
        data = self._baileys_call('GET', f'/session/{self.baileys_session_id}/status')
        if not data:
            return self._connect_notify(
                False, _('Bridge did not respond. Check it is running and the URL/API key are correct '
                          '(see the chatter on this record for the exact error).'))
        state = data.get('state')
        if state == 'connected':
            return self._connect_notify(True, _('Connected - paired to %s.') % (data.get('phone_number') or '?'))
        if state == 'qr_pending':
            return self._connect_notify(False, _('Bridge is up, but this number has not scanned its QR code yet.'))
        return self._connect_notify(False, _('Bridge is up but this session is disconnected. Start pairing again.'))

    def _test_meta_page_connection(self):
        self.ensure_one()
        if not self.page_access_token:
            return self._connect_notify(False, _('No Page Access Token set - connect this Page from '
                                                   'Settings > Omnichannel > Connections.'))
        import requests
        try:
            resp = requests.get(
                f'https://graph.facebook.com/v19.0/{self.meta_page_id}',
                params={'fields': 'name,id', 'access_token': self.page_access_token}, timeout=10)
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return self._connect_notify(False, _('Could not reach Graph API: %s') % e)
        if 'error' in data:
            return self._connect_notify(False, _('Token rejected: %s') % data['error'].get('message', ''))
        return self._connect_notify(True, _('Connected - Page "%s" token is valid.') % data.get('name', ''))

    def _test_voip_connection(self):
        """Two-part check: (1) can we log into Asterisk's AMI with these
        credentials at all, and (2) if a bridge health URL is configured
        globally, is the long-lived event bridge actually up too - a call
        can originate fine (part 1 only) while ringing/answered/hangup
        never syncs back because ami_bridge.py isn't running."""
        self.ensure_one()
        if not (self.ami_host and self.ami_username and self.ami_secret):
            return self._connect_notify(False, _('Set AMI Host, Username and Secret first.'))
        from odoo.addons.crm_omnichannel_voip_asterisk.models.asterisk_ami import AsteriskAMI, AsteriskAMIError
        try:
            with AsteriskAMI(self.ami_host, self.ami_port, self.ami_username, self.ami_secret, timeout=6):
                pass
        except AsteriskAMIError as e:
            return self._connect_notify(False, _('AMI login failed: %s') % e)
        except OSError as e:
            return self._connect_notify(False, _('Could not reach %s:%s: %s')
                                         % (self.ami_host, self.ami_port, e))

        bridge_url = self.env['ir.config_parameter'].sudo().get_param(
            'crm_omnichannel_connect_center.ami_bridge_health_url')
        if not bridge_url:
            return self._connect_notify(
                True, _('AMI login succeeded. Note: no Bridge Health URL is set in Settings, so live call-event '
                         'sync (ringing/answered/hangup) could not be verified here.'))
        import requests
        try:
            resp = requests.get(f'{bridge_url.rstrip("/")}/health', timeout=8)
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return self._connect_notify(False, _('AMI login OK, but the event bridge is unreachable at %s: %s. '
                                                   'Outbound calls will work but live status sync will not.')
                                         % (bridge_url, e))
        if not data.get('ami_connected'):
            return self._connect_notify(False, _('AMI login OK and the bridge process is running, but the bridge '
                                                   'itself is not connected to Asterisk - check its logs.'))
        return self._connect_notify(True, _('Fully connected - AMI login OK and the event bridge is live.'))

    def _connect_notify(self, success, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Connection OK') if success else _('Connection problem'),
                'message': message,
                'type': 'success' if success else 'danger',
                'sticky': not success,
            },
        }
