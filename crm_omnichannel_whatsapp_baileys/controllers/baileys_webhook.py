# -*- coding: utf-8 -*-
"""
Webhook receiver for the Baileys bridge microservice (bridge/server.js).

Auth model: every call carries header X-Bridge-Api-Key. We look up the
crm.channel whose baileys_session_id matches the payload's session_id,
then compare its baileys_api_key. Unlike Meta's HMAC signature (we don't
control the bridge's transport), a shared-secret header is enough here
since this endpoint should only ever be reachable from your own bridge
(put it behind the same reverse proxy / firewall as the bridge itself).

Event shapes pushed by the bridge:
  {"event": "qr",         "session_id": "...", "qr_base64": "<png b64>"}
  {"event": "connection", "session_id": "...", "state": "connected|qr_pending|disconnected",
                           "phone_number": "8801..."}
  {"event": "message",    "session_id": "...", "from": "8801...@s.whatsapp.net",
                           "name": "Customer Name", "message_id": "...",
                           "type": "text|image|video|audio|document|sticker|location|contact",
                           "text": "...", "media_url": "https://.../file.jpg",
                           "caption": "...", "timestamp": 1712345678}
"""
import base64
import hmac
import ipaddress
import json
import logging
import socket
from urllib.parse import urlparse

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BaileysWebhookController(http.Controller):

    @http.route('/omni/webhook/whatsapp_baileys', type='http', auth='public', methods=['POST'], csrf=False)
    def baileys_webhook(self, **kwargs):
        raw_body = request.httprequest.get_data()
        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            _logger.warning('Baileys webhook: could not parse JSON body.')
            return request.make_json_response({'ok': False, 'error': 'bad json'}, status=400)

        session_id = payload.get('session_id')
        if not session_id:
            return request.make_json_response({'ok': False, 'error': 'missing session_id'}, status=400)

        channel = request.env['crm.channel'].sudo().search([
            ('baileys_session_id', '=', session_id),
            ('whatsapp_provider', '=', 'baileys'),
        ], limit=1)
        if not channel:
            _logger.info('Baileys webhook: no channel configured for session_id %s.', session_id)
            return request.make_json_response({'ok': False, 'error': 'unknown session_id'}, status=404)

        api_key = request.httprequest.headers.get('X-Bridge-Api-Key', '')
        if not channel.baileys_api_key or not hmac.compare_digest(api_key, channel.baileys_api_key):
            _logger.warning('Baileys webhook: bad/missing API key for channel %s.', channel.name)
            return request.make_json_response({'ok': False, 'error': 'forbidden'}, status=403)

        event = payload.get('event')
        try:
            if event == 'qr':
                self._handle_qr(channel, payload)
            elif event == 'connection':
                self._handle_connection(channel, payload)
            elif event == 'message':
                self._handle_message(channel, payload)
            elif event == 'ack':
                self._handle_ack(channel, payload)
            else:
                _logger.info('Baileys webhook: unhandled event type "%s" from channel %s.', event, channel.name)
        except Exception:
            # Same principle as the Meta webhook: never let one bad payload
            # take down the endpoint or leave the bridge retrying forever.
            _logger.exception('Error processing Baileys webhook event %s for channel %s', event, channel.name)
            return request.make_json_response({'ok': False, 'error': 'internal error, logged'}, status=200)

        return request.make_json_response({'ok': True})

    # =====================================================================
    # EVENT HANDLERS
    # =====================================================================
    def _handle_qr(self, channel, payload):
        qr_b64 = payload.get('qr_base64', '')
        channel.sudo().write({
            'baileys_connection_state': 'qr_pending',
            'baileys_qr_image': qr_b64,
            'baileys_qr_updated': fields.Datetime.now(),
        })

    def _handle_connection(self, channel, payload):
        vals = {'baileys_last_seen': fields.Datetime.now()}
        state = payload.get('state')
        if state in ('connected', 'qr_pending', 'disconnected'):
            vals['baileys_connection_state'] = state
        if state == 'connected':
            vals['baileys_qr_image'] = False
            if payload.get('phone_number'):
                vals['baileys_connected_number'] = payload['phone_number']
                if not channel.account_identifier:
                    vals['account_identifier'] = payload['phone_number']
        channel.sudo().write(vals)

    def _handle_ack(self, channel, payload):
        """Delivery / read receipt for an outbound message we already sent."""
        external_message_id = payload.get('message_id')
        status = payload.get('status')  # 'delivered' | 'read'
        if not external_message_id:
            return
        message = request.env['crm.chat.message'].sudo().search(
            [('external_message_id', '=', external_message_id)], limit=1)
        if not message:
            return
        if status == 'delivered':
            message.write({'is_delivered': True})
        elif status == 'read':
            message.write({'is_delivered': True, 'is_seen': True})

    def _handle_message(self, channel, payload):
        wa_id = payload.get('from')
        external_message_id = payload.get('message_id')
        if not wa_id:
            return
        if external_message_id and request.env['crm.chat.message'].sudo().search_count(
                [('external_message_id', '=', external_message_id)]):
            return  # duplicate webhook delivery

        msg_type = payload.get('type', 'text')
        mapped_type = msg_type if msg_type in (
            'image', 'video', 'audio', 'document', 'sticker', 'location', 'contact') else 'text'
        body = payload.get('text') or payload.get('caption') or ''
        if mapped_type == 'location' and not body:
            body = '%s, %s' % (payload.get('latitude'), payload.get('longitude'))

        Channel = request.env['crm.channel']
        Session = request.env['crm.chat.session'].sudo()
        session = Session.search([
            ('channel_id', '=', channel.id),
            ('external_identifier', '=', wa_id),
            ('state', '!=', 'spam'),
        ], limit=1)
        if not session:
            session = Session.with_context(first_message_body=body).create({
                'channel_id': channel.id,
                'external_identifier': wa_id,
                'partner_name': payload.get('name'),
            })

        message_vals = {
            'session_id': session.id,
            'direction': 'in',
            'body': body,
            'message_type': mapped_type,
            'external_message_id': external_message_id,
            'message_date': fields.Datetime.now(),
        }
        message = request.env['crm.chat.message'].sudo().create(message_vals)

        media_url = payload.get('media_url')
        if media_url and mapped_type != 'text':
            self._attach_media(message, media_url, msg_type, channel)

    # Hard cap on downloaded media size (bytes) - avoids a hostile/compromised
    # bridge exhausting memory/disk via a single "media" event.
    _MAX_MEDIA_BYTES = 25 * 1024 * 1024

    def _attach_media(self, message, media_url, msg_type, channel):
        """Download the media the bridge already hosted for us and attach it,
        so agents see images/voice notes inline instead of a bare link.

        media_url comes from the webhook payload, i.e. from whatever sent the
        (api-key-authenticated) request. We still don't want to turn this
        into a generic server-side-request-forgery primitive against the
        Odoo host's internal network, so: only http(s), only the bridge's
        own configured host, and no requests that resolve to a private/
        loopback/link-local address.
        """
        import requests

        if not self._is_safe_media_url(media_url, channel):
            _logger.warning('Baileys webhook: refusing to fetch untrusted/unsafe media URL %r for channel %s.',
                             media_url, channel.name)
            return

        try:
            resp = requests.get(media_url, timeout=20, stream=True, allow_redirects=False)
            resp.raise_for_status()
            content = resp.raw.read(self._MAX_MEDIA_BYTES + 1, decode_content=True)
            if len(content) > self._MAX_MEDIA_BYTES:
                _logger.warning('Baileys webhook: media at %s exceeds size limit, skipping attachment.', media_url)
                return
        except requests.exceptions.RequestException:
            _logger.exception('Could not download inbound Baileys media from %s', media_url)
            return
        finally:
            try:
                resp.close()
            except Exception:
                pass

        attachment = request.env['ir.attachment'].sudo().create({
            'name': f'{msg_type}_{message.id}',
            'datas': base64.b64encode(content),
            'res_model': 'crm.chat.message',
            'res_id': message.id,
        })
        message.sudo().write({'attachment_ids': [(4, attachment.id)]})

    def _is_safe_media_url(self, media_url, channel):
        try:
            parsed = urlparse(media_url)
        except ValueError:
            return False
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            return False

        # Restrict to the same host as the channel's configured bridge, so a
        # compromised/malicious bridge can't use this endpoint to make Odoo
        # fetch arbitrary internal URLs on its behalf.
        bridge_host = urlparse(channel.baileys_base_url or '').hostname
        if not bridge_host or parsed.hostname.lower() != bridge_host.lower():
            return False

        try:
            addrs = socket.getaddrinfo(parsed.hostname, None)
        except socket.gaierror:
            return False
        for family, _type, _proto, _canon, sockaddr in addrs:
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
