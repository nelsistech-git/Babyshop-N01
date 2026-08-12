# -*- coding: utf-8 -*-
import secrets

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # --- Meta App (shared by every Facebook Page / Instagram account you connect) ---
    connect_meta_app_id = fields.Char(
        string='Meta App ID', config_parameter='crm_omnichannel_connect_center.meta_app_id')
    connect_meta_app_secret = fields.Char(
        string='Meta App Secret', config_parameter='crm_omnichannel_connect_center.meta_app_secret')
    connect_meta_verify_token = fields.Char(
        string='Webhook Verify Token', config_parameter='crm_omnichannel_connect_center.meta_verify_token',
        help='Auto-generated once. Paste this, together with the Webhook Callback URL below, '
             'into Meta App Dashboard > Webhooks - this is the ONE manual step Meta requires '
             'per App (not per Page/number), and it cannot be done via API.')
    connect_meta_webhook_url = fields.Char(string='Webhook Callback URL', compute='_compute_meta_urls')
    connect_meta_oauth_redirect_uri = fields.Char(string='OAuth Redirect URI', compute='_compute_meta_urls')

    # --- Baileys bridge defaults (so the "Add Number" wizard doesn't ask every time) ---
    connect_baileys_default_url = fields.Char(
        string='Baileys Bridge URL', config_parameter='crm_omnichannel_connect_center.baileys_default_url',
        help='Base URL of your running bridge/server.js, e.g. https://wa-bridge.yourdomain.com')
    connect_baileys_default_api_key = fields.Char(
        string='Baileys Bridge API Key', config_parameter='crm_omnichannel_connect_center.baileys_default_api_key')

    # --- Asterisk VoIP defaults (so the "Add Calling Line" wizard doesn't ask every time) ---
    connect_ami_default_host = fields.Char(
        string='AMI Host', config_parameter='crm_omnichannel_connect_center.ami_default_host')
    connect_ami_default_port = fields.Integer(
        string='AMI Port', config_parameter='crm_omnichannel_connect_center.ami_default_port', default=5038)
    connect_ami_default_username = fields.Char(
        string='AMI Username', config_parameter='crm_omnichannel_connect_center.ami_default_username')
    connect_ami_default_secret = fields.Char(
        string='AMI Secret', config_parameter='crm_omnichannel_connect_center.ami_default_secret')
    connect_ami_bridge_health_url = fields.Char(
        string='AMI Bridge Health URL', config_parameter='crm_omnichannel_connect_center.ami_bridge_health_url',
        help='Base URL where ami_bridge.py exposes its /health endpoint, e.g. '
             'http://localhost:8088 (see BRIDGE_SETUP.md - the bridge script now serves '
             'a small health-check HTTP endpoint alongside its AMI connection).')
    connect_ami_webhook_url = fields.Char(string='Call Event Webhook URL', compute='_compute_meta_urls')

    @api.depends('connect_meta_app_id')
    def _compute_meta_urls(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.connect_meta_webhook_url = f'{base_url}/omni/webhook/meta'
            rec.connect_meta_oauth_redirect_uri = f'{base_url}/omni/connect/facebook/return'
            rec.connect_ami_webhook_url = f'{base_url}/omni/webhook/asterisk'

    @api.model
    def get_values(self):
        res = super().get_values()
        # Auto-generate the verify token the first time this screen is opened,
        # so there's always something valid to paste into the Meta Dashboard.
        icp = self.env['ir.config_parameter'].sudo()
        if not icp.get_param('crm_omnichannel_connect_center.meta_verify_token'):
            icp.set_param('crm_omnichannel_connect_center.meta_verify_token', secrets.token_urlsafe(24))
        return res

    def action_test_baileys_bridge(self):
        """Ping the bridge's /health endpoint with the configured default URL/key,
        so a broken bridge is reported here instead of only failing silently
        later when someone tries to pair a number."""
        self.ensure_one()
        import requests
        url = (self.connect_baileys_default_url or '').rstrip('/')
        if not url:
            return self._notify(False, 'Set the Baileys Bridge URL first.')
        try:
            resp = requests.get(f'{url}/health', timeout=8)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return self._notify(False, f'Could not reach the bridge at {url}: {e}')
        except ValueError:
            return self._notify(False, f'Bridge at {url} responded but not with valid JSON. '
                                        f'Is this really the Baileys bridge URL?')
        return self._notify(True, f'Bridge reachable. Active sessions on bridge: {data.get("sessions", 0)}.')

    def action_test_meta_credentials(self):
        """Call Graph API with the App ID/Secret to confirm they're valid,
        instead of only discovering a typo when a webhook silently fails."""
        self.ensure_one()
        import requests
        if not (self.connect_meta_app_id and self.connect_meta_app_secret):
            return self._notify(False, 'Enter both Meta App ID and App Secret first.')
        try:
            resp = requests.get(
                'https://graph.facebook.com/oauth/access_token',
                params={
                    'client_id': self.connect_meta_app_id,
                    'client_secret': self.connect_meta_app_secret,
                    'grant_type': 'client_credentials',
                },
                timeout=10,
            )
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return self._notify(False, f'Could not reach Graph API: {e}')
        if 'access_token' in data:
            return self._notify(True, 'Meta App ID / Secret are valid.')
        error_msg = (data.get('error') or {}).get('message', 'Unknown error')
        return self._notify(False, f'Meta rejected these credentials: {error_msg}')

    def action_test_ami_credentials(self):
        """Synchronous AMI login/logoff against the default host/port/user/secret,
        so a bad password is caught here instead of failing silently the next
        time an agent clicks Call."""
        self.ensure_one()
        if not (self.connect_ami_default_host and self.connect_ami_default_username
                and self.connect_ami_default_secret):
            return self._notify(False, 'Set AMI Host, Username and Secret first.')
        from odoo.addons.crm_omnichannel_voip_asterisk.models.asterisk_ami import AsteriskAMI, AsteriskAMIError
        try:
            with AsteriskAMI(self.connect_ami_default_host, self.connect_ami_default_port,
                              self.connect_ami_default_username, self.connect_ami_default_secret, timeout=6):
                pass
        except AsteriskAMIError as e:
            return self._notify(False, f'AMI login failed: {e}')
        except OSError as e:
            return self._notify(False, f'Could not reach {self.connect_ami_default_host}:'
                                        f'{self.connect_ami_default_port}: {e}')
        return self._notify(True, 'AMI login succeeded - Asterisk accepted these credentials.')

    def action_test_ami_bridge_health(self):
        """Ping ami_bridge.py's /health endpoint - a green AMI login test only
        proves Asterisk itself is reachable, NOT that the separate long-lived
        event bridge (which is what actually syncs ringing/answered/hangup
        into Odoo in real time) is up. This is the check that catches
        'calls connect but nothing updates in the CRM'."""
        self.ensure_one()
        import requests
        url = (self.connect_ami_bridge_health_url or '').rstrip('/')
        if not url:
            return self._notify(False, 'Set the AMI Bridge Health URL first (see BRIDGE_SETUP.md).')
        try:
            resp = requests.get(f'{url}/health', timeout=8)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return self._notify(False, f'Could not reach the AMI bridge at {url}: {e}')
        except ValueError:
            return self._notify(False, f'Bridge at {url} responded but not with valid JSON.')
        ami_state = 'connected' if data.get('ami_connected') else 'NOT connected to Asterisk'
        return self._notify(data.get('ami_connected', False),
                             f'AMI bridge process is up, AMI link is {ami_state}.')

    def _notify(self, success, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Connection OK' if success else 'Connection failed',
                'message': message,
                'type': 'success' if success else 'danger',
                'sticky': not success,
            },
        }
