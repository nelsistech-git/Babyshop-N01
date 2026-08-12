# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)

# Map our internal message_type to the type string the bridge understands.
_TYPE_MAP = {
    'text': 'text', 'image': 'image', 'video': 'video', 'audio': 'audio',
    'document': 'document', 'sticker': 'sticker', 'template': 'text',
}


class CrmChatMessage(models.Model):
    _inherit = 'crm.chat.message'

    def _send_whatsapp_message(self, channel):
        """crm_omnichannel_meta_connector calls this for every outbound
        WhatsApp message. Branch here instead of re-touching the base
        Cloud API path, so both providers keep working side by side."""
        if channel.whatsapp_provider == 'baileys':
            return self._send_whatsapp_via_baileys(channel)
        return super()._send_whatsapp_message(channel)

    def _send_whatsapp_via_baileys(self, channel):
        self.ensure_one()
        if channel.baileys_connection_state != 'connected':
            _logger.warning('Baileys channel %s is not connected (state=%s); sending anyway, '
                             'bridge will queue or fail it.', channel.name, channel.baileys_connection_state)
        if not (channel.baileys_base_url and channel.baileys_session_id and channel.baileys_api_key):
            _logger.warning('Baileys credentials incomplete on channel %s; skipping send.', channel.name)
            self.session_id.message_post(
                body='Message not sent: the Baileys connector on this channel is not fully configured.')
            return

        import requests
        payload = {
            'session_id': channel.baileys_session_id,
            'to': self.session_id.external_identifier,
            'type': _TYPE_MAP.get(self.message_type, 'text'),
        }
        if self.message_type == 'text' or self.message_type == 'template':
            payload['text'] = self.body or ''
        else:
            # Media messages: send the first attachment's public/download URL,
            # the bridge fetches and re-uploads it to WhatsApp on its side.
            attachment = self.attachment_ids[:1]
            if not attachment:
                _logger.warning('Outbound %s message %s has no attachment; sending as text instead.',
                                 self.message_type, self.id)
                payload['type'] = 'text'
                payload['text'] = self.body or ''
            else:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                payload['media_url'] = f'{base_url}/web/content/{attachment.id}?download=true'
                payload['caption'] = self.body or ''

        url = channel.baileys_base_url.rstrip('/') + '/send'
        headers = {'X-Bridge-Api-Key': channel.baileys_api_key, 'Content-Type': 'application/json'}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
        except requests.exceptions.RequestException:
            _logger.exception('Failed to reach Baileys bridge for message %s', self.id)
            self.session_id.message_post(
                body='Message delivery failed: could not reach the Baileys bridge. Check it is running.')
            return

        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code >= 400 or not data.get('ok', True):
            _logger.error('Baileys bridge send error for message %s: %s', self.id, data or response.text)
            self.session_id.message_post(
                body='Message delivery failed via Baileys (HTTP %s): %s' % (
                    response.status_code, data.get('error') or response.text[:200]))
            return

        external_id = data.get('message_id')
        if external_id:
            self.sudo().write({'external_message_id': external_id, 'is_delivered': True})
