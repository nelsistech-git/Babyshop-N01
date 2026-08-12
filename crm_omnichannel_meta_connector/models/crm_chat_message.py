# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

GRAPH_API_VERSION = 'v19.0'
GRAPH_API_BASE = f'https://graph.facebook.com/{GRAPH_API_VERSION}'


class CrmChatMessage(models.Model):
    _inherit = 'crm.chat.message'

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        for message in messages:
            if message.direction == 'out' and not message.external_message_id:
                message._send_via_meta()
        return messages

    # =====================================================================
    # DISPATCH
    # =====================================================================
    def _send_via_meta(self):
        self.ensure_one()
        channel = self.session_id.channel_id
        try:
            if channel.code == 'facebook':
                self._send_facebook_message(channel)
            elif channel.code == 'instagram':
                self._send_instagram_message(channel)
            elif channel.code == 'whatsapp':
                self._send_whatsapp_message(channel)
        except Exception:
            # Never let a delivery failure block the agent from saving their
            # reply in Odoo - log it on the record so it's visible, and let
            # a human notice and resend / follow up manually.
            _logger.exception('Failed to deliver outbound message %s via %s', self.id, channel.code)
            self.session_id.message_post(
                body='Failed to deliver the last outbound message via %s. '
                     'Check the server log and the recipient\'s access token.' % (channel.name or channel.code))

    # =====================================================================
    # FACEBOOK MESSENGER
    # https://developers.facebook.com/docs/messenger-platform/send-messages
    # =====================================================================
    def _send_facebook_message(self, channel):
        if not channel.page_access_token:
            _logger.warning('No Page Access Token configured on channel %s; skipping send.', channel.name)
            return
        import requests
        url = f'{GRAPH_API_BASE}/me/messages'
        payload = {
            'recipient': {'id': self.session_id.external_identifier},
            'message': {'text': self.body or ''},
            'messaging_type': 'RESPONSE',
        }
        response = requests.post(
            url, params={'access_token': channel.page_access_token}, json=payload, timeout=10)
        self._store_send_result(response)

    # =====================================================================
    # INSTAGRAM
    # https://developers.facebook.com/docs/messenger-platform/instagram
    # =====================================================================
    def _send_instagram_message(self, channel):
        if not channel.page_access_token:
            _logger.warning('No Page Access Token configured on channel %s; skipping send.', channel.name)
            return
        import requests
        # Instagram DMs are sent through the same Send API as Messenger,
        # authenticated with the Page (not IG User) access token.
        url = f'{GRAPH_API_BASE}/me/messages'
        payload = {
            'recipient': {'id': self.session_id.external_identifier},
            'message': {'text': self.body or ''},
        }
        response = requests.post(
            url, params={'access_token': channel.page_access_token}, json=payload, timeout=10)
        self._store_send_result(response)

    # =====================================================================
    # WHATSAPP (Cloud API)
    # https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages
    # =====================================================================
    def _send_whatsapp_message(self, channel):
        if not channel.whatsapp_access_token or not channel.whatsapp_phone_number_id:
            _logger.warning('WhatsApp credentials incomplete on channel %s; skipping send.', channel.name)
            return
        import requests
        url = f'{GRAPH_API_BASE}/{channel.whatsapp_phone_number_id}/messages'
        payload = {
            'messaging_product': 'whatsapp',
            'to': self.session_id.external_identifier,
            'type': 'text',
            'text': {'body': self.body or ''},
        }
        headers = {
            'Authorization': f'Bearer {channel.whatsapp_access_token}',
            'Content-Type': 'application/json',
        }
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        self._store_send_result(response)

    # =====================================================================
    # HELPERS
    # =====================================================================
    def _store_send_result(self, response):
        self.ensure_one()
        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code >= 400:
            _logger.error('Meta send API error for message %s: %s', self.id, data or response.text)
            self.session_id.message_post(
                body='Message delivery failed (HTTP %s): %s' % (response.status_code, data))
            return
        external_id = data.get('message_id') or (data.get('messages') or [{}])[0].get('id')
        if external_id:
            self.sudo().write({'external_message_id': external_id, 'is_delivered': True})
