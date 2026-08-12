# -*- coding: utf-8 -*-
"""
Webhook receiver for bridge/ami_bridge.py - a small standalone daemon that
holds the persistent AMI event-stream connection to Asterisk (AMI doesn't
fit a normal Odoo HTTP worker) and forwards each event here as JSON.

Expected payload shape:
{
  "channel_name": "<crm.channel name, or omit if you only run one>",
  "event": "ring" | "answer" | "hold" | "unhold" | "hangup" | "recording_ready",
  "uniqueid": "<Asterisk unique call id>",
  "caller_number": "+8801...",
  "quickcrm_call_id": "123",       # only present if WE originated the call
  "recording_url": "https://..."   # only for recording_ready
}
"""
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AsteriskWebhookController(http.Controller):

    @http.route('/omni/webhook/asterisk', type='http', auth='public', methods=['POST'], csrf=False)
    def asterisk_webhook(self, **kwargs):
        raw_body = request.httprequest.get_data()
        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return request.make_json_response({'ok': False, 'error': 'bad json'}, status=400)

        Channel = request.env['crm.channel'].sudo()
        channel_name = payload.get('channel_name')
        domain = [('code', '=', 'call')]
        if channel_name:
            domain.append(('name', '=', channel_name))
        channel = Channel.search(domain, limit=1)
        if not channel:
            _logger.info('Asterisk webhook: no IP Calling channel found (channel_name=%s).', channel_name)
            return request.make_json_response({'ok': False, 'error': 'unknown channel'}, status=404)

        secret = request.httprequest.headers.get('X-Bridge-Api-Key', '')
        if not channel.ami_webhook_secret or not hmac.compare_digest(secret, channel.ami_webhook_secret):
            _logger.warning('Asterisk webhook: bad/missing secret for channel %s.', channel.name)
            return request.make_json_response({'ok': False, 'error': 'forbidden'}, status=403)

        try:
            request.env['crm.call.log'].sudo()._asterisk_sync_event(channel, payload)
        except Exception:
            _logger.exception('Error processing Asterisk webhook event: %s', payload)
            return request.make_json_response({'ok': False, 'error': 'internal error, logged'}, status=200)

        return request.make_json_response({'ok': True})
