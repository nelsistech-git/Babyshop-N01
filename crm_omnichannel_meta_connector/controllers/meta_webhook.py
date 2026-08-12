# -*- coding: utf-8 -*-
"""
Webhook receiver for Facebook Messenger, Instagram and WhatsApp (all under
Meta's Graph API umbrella).

CAVEAT (see also the module description / README notice): this was written
against Meta's publicly documented webhook payload shapes. It has not been
exercised against a live webhook delivery in this environment (no outbound
network access here). Meta's exact JSON structure - especially for
Instagram DMs, which has changed more than once historically - should be
verified against real payloads (check the server log; every payload is
logged at DEBUG level before parsing) and the `_process_*` methods below
adjusted if needed before relying on this in production.
"""
import hashlib
import hmac
import json
import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MetaWebhookController(http.Controller):

    # =====================================================================
    # WEBHOOK VERIFICATION (Meta calls this once, as a GET, when you save
    # the webhook URL in the App Dashboard)
    # =====================================================================
    @http.route('/omni/webhook/meta', type='http', auth='public', methods=['GET'], csrf=False)
    def meta_webhook_verify(self, **kwargs):
        mode = kwargs.get('hub.mode')
        token = kwargs.get('hub.verify_token')
        challenge = kwargs.get('hub.challenge', '')

        if not (mode == 'subscribe' and token):
            return request.make_response('Forbidden', status=403)

        channel = request.env['crm.channel'].sudo().search([('verify_token', '=', token)], limit=1)
        if not channel:
            _logger.warning('Meta webhook verification failed: no channel with matching verify_token.')
            return request.make_response('Forbidden', status=403)

        return request.make_response(challenge)

    # =====================================================================
    # WEBHOOK RECEIVER (Meta calls this as a POST for every event)
    # =====================================================================
    @http.route('/omni/webhook/meta', type='http', auth='public', methods=['POST'], csrf=False)
    def meta_webhook_receive(self, **kwargs):
        raw_body = request.httprequest.get_data()
        signature_header = request.httprequest.headers.get('X-Hub-Signature-256', '')

        _logger.debug('Meta webhook raw payload: %s', raw_body)

        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            _logger.warning('Meta webhook: could not parse JSON body.')
            return request.make_response('Bad Request', status=400)

        object_type = payload.get('object')
        for entry in payload.get('entry', []):
            try:
                if object_type == 'whatsapp_business_account':
                    self._handle_whatsapp_entry(entry, raw_body, signature_header)
                else:
                    # object_type is 'page' for Messenger, 'instagram' for Instagram.
                    self._handle_page_entry(entry, object_type, raw_body, signature_header)
            except Exception:
                # One malformed / unexpected entry should never take down the
                # whole webhook response (Meta will retry on non-200).
                _logger.exception('Error processing Meta webhook entry: %s', entry)

        # Meta requires a fast 200 response regardless of internal outcome,
        # or it will keep retrying the same delivery.
        return request.make_response('EVENT_RECEIVED', status=200)

    # =====================================================================
    # MESSENGER / INSTAGRAM ("page" / "instagram" object type)
    # =====================================================================
    def _handle_page_entry(self, entry, object_type, raw_body, signature_header):
        page_or_ig_id = entry.get('id')
        channel = self._find_channel(object_type, page_or_ig_id)
        if not channel:
            _logger.info('Meta webhook: no channel configured for %s id %s.', object_type, page_or_ig_id)
            return
        if not self._verify_signature(channel, raw_body, signature_header):
            _logger.warning('Meta webhook: signature verification failed for channel %s.', channel.name)
            return

        # Messenger and Instagram DMs both typically arrive under 'messaging'.
        for event in entry.get('messaging', []):
            self._process_messaging_event(channel, event)

        # Comments / mentions (Instagram) arrive under 'changes' instead -
        # not mapped to chat sessions by default since they aren't private
        # conversations; logged for visibility only.
        for change in entry.get('changes', []):
            _logger.info('Meta webhook: received unhandled "changes" event (comment/mention?) for channel %s: %s',
                         channel.name, change.get('field'))

    def _process_messaging_event(self, channel, event):
        message = event.get('message')
        sender_id = (event.get('sender') or {}).get('id')
        if not message or not sender_id:
            return
        if message.get('is_echo'):
            # This is a delivery receipt for our own outbound message, not
            # a new inbound message - ignore it.
            return

        external_message_id = message.get('mid')
        if external_message_id and request.env['crm.chat.message'].sudo().search_count(
                [('external_message_id', '=', external_message_id)]):
            return  # duplicate webhook delivery

        body = message.get('text') or ''
        message_type = 'text'
        attachments = message.get('attachments') or []
        if attachments:
            first = attachments[0]
            message_type = self._map_attachment_type(first.get('type'))
            if not body:
                body = (first.get('payload') or {}).get('url', '')

        session = self._get_or_create_session(channel, sender_id, first_message_body=body)
        request.env['crm.chat.message'].sudo().create({
            'session_id': session.id,
            'direction': 'in',
            'body': body,
            'message_type': message_type,
            'external_message_id': external_message_id,
            'message_date': fields.Datetime.now(),
        })

    # =====================================================================
    # WHATSAPP ("whatsapp_business_account" object type)
    # =====================================================================
    def _handle_whatsapp_entry(self, entry, raw_body, signature_header):
        for change in entry.get('changes', []):
            value = change.get('value') or {}
            phone_number_id = (value.get('metadata') or {}).get('phone_number_id')
            channel = request.env['crm.channel'].sudo().search([
                ('whatsapp_phone_number_id', '=', phone_number_id)], limit=1)
            if not channel:
                _logger.info('Meta webhook: no WhatsApp channel configured for phone_number_id %s.', phone_number_id)
                continue
            if not self._verify_signature(channel, raw_body, signature_header):
                _logger.warning('Meta webhook: signature verification failed for channel %s.', channel.name)
                continue

            contacts = {c.get('wa_id'): (c.get('profile') or {}).get('name')
                        for c in value.get('contacts', [])}

            for msg in value.get('messages', []):
                self._process_whatsapp_message(channel, msg, contacts)

    def _process_whatsapp_message(self, channel, msg, contacts):
        wa_id = msg.get('from')
        external_message_id = msg.get('id')
        if not wa_id:
            return
        if external_message_id and request.env['crm.chat.message'].sudo().search_count(
                [('external_message_id', '=', external_message_id)]):
            return  # duplicate webhook delivery

        msg_type = msg.get('type', 'text')
        body = ''
        mapped_type = 'text'
        if msg_type == 'text':
            body = (msg.get('text') or {}).get('body', '')
        elif msg_type in ('image', 'video', 'audio', 'document', 'sticker'):
            mapped_type = msg_type if msg_type != 'sticker' else 'sticker'
            media = msg.get(msg_type) or {}
            body = media.get('caption', '') or media.get('id', '')
        elif msg_type == 'location':
            mapped_type = 'location'
            loc = msg.get('location') or {}
            body = '%s, %s' % (loc.get('latitude'), loc.get('longitude'))
        elif msg_type == 'contacts':
            mapped_type = 'contact'
            body = json.dumps(msg.get('contacts'))
        else:
            body = json.dumps(msg)

        session = self._get_or_create_session(channel, wa_id, name=contacts.get(wa_id), first_message_body=body)
        request.env['crm.chat.message'].sudo().create({
            'session_id': session.id,
            'direction': 'in',
            'body': body,
            'message_type': mapped_type,
            'external_message_id': external_message_id,
            'message_date': fields.Datetime.now(),
        })

    # =====================================================================
    # SHARED HELPERS
    # =====================================================================
    def _find_channel(self, object_type, external_id):
        Channel = request.env['crm.channel'].sudo()
        if object_type == 'instagram':
            return Channel.search([('meta_ig_account_id', '=', external_id)], limit=1)
        # default: Messenger ('page')
        return Channel.search([('meta_page_id', '=', external_id)], limit=1)

    def _verify_signature(self, channel, raw_body, signature_header):
        if not channel.app_secret:
            _logger.warning(
                'Channel %s has no App Secret configured - rejecting webhook for safety. '
                'Configure the App Secret on the channel to enable signature verification.',
                channel.name)
            return False
        if not signature_header or not signature_header.startswith('sha256='):
            return False
        expected = 'sha256=' + hmac.new(
            channel.app_secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)

    def _get_or_create_session(self, channel, external_identifier, name=None, first_message_body=None):
        Session = request.env['crm.chat.session'].sudo()
        session = Session.search([
            ('channel_id', '=', channel.id),
            ('external_identifier', '=', external_identifier),
            ('state', '!=', 'spam'),
        ], limit=1)
        if session:
            return session
        if first_message_body:
            Session = Session.with_context(first_message_body=first_message_body)
        return Session.create({
            'channel_id': channel.id,
            'external_identifier': external_identifier,
            'partner_name': name,
        })

    def _map_attachment_type(self, meta_type):
        return {
            'image': 'image',
            'video': 'video',
            'audio': 'audio',
            'file': 'document',
            'template': 'template',
        }.get(meta_type, 'text')
