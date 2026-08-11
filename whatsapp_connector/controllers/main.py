# -*- coding: utf-8 -*-
import logging
import json
import warnings
import os
import subprocess
from io import BytesIO
from werkzeug.datastructures import FileStorage
from tempfile import NamedTemporaryFile
from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import UserError
from ..models.Message import INSTAGRAM_AUDIO_FORMAT_ALLOWED
from ..models.Message import INSTAGRAM_VIDEO_FORMAT_ALLOWED
_logger = logging.getLogger(__name__)


try:
    saved_warning_state = warnings.filters[:]
    warnings.simplefilter('ignore')
    import pydub
except Exception:
    pydub = None
finally:
    warnings.filters = saved_warning_state


def log_request(req):
    pass


def acrux_allowed_models():
    return ['product.template', 'product.product', 'acrux.chat.new.group.wizard', 'acrux.chat.conversation']


class WebhookController(http.Controller):

    @http.route('/acrux_webhook/test', auth='public', type='http')
    def acrux_webhook_test(self, **post):
        # http://localhost:8014/acrux_webhook/test
        from datetime import datetime
        WorkQueue = request.env['acrux.chat.work.queue'].sudo()
        WorkQueue.queue_trigger()
        txt = datetime.now().strftime("%H:%M:%S.%f")
        return Response(txt, status=200)

    @http.route('/acrux_webhook/whatsapp_connector/<string:connector_uuid>',
                auth='public', type='http', methods=['GET', 'POST'], csrf=False)
    def acrux_webhook(self, connector_uuid, **post):
        '''WhatsApp gateway (POST JSON) or Facebook Messenger webhook (GET verify + POST Meta payload).'''
        Connector = request.env['acrux.chat.connector'].sudo()
        connector_id = Connector.search([('uuid', '=', connector_uuid)], limit=1)
        if not connector_uuid or not connector_id:
            return Response(status=404)

        def _clean_hub_str(val):
            s = '' if val is None else str(val).strip().lstrip('\ufeff').strip()
            return s

        def _hub_query_get(key_primary, key_alt):
            """Parse Meta verification query (?hub.mode=… etc.). Odoo merges args into ``request.params`` too."""
            args = request.httprequest.args
            raw = args.get(key_primary) or args.get(key_alt)
            if not raw:
                try:
                    merged = getattr(request, 'params', None) or {}
                    raw = merged.get(key_primary) or merged.get(key_alt)
                except Exception:
                    raw = ''
            return _clean_hub_str(raw)

        if request.httprequest.method == 'GET':
            hub_mode = _hub_query_get('hub.mode', 'hub_mode')
            hub_challenge = _hub_query_get('hub.challenge', 'hub_challenge')
            hub_verify = _hub_query_get('hub.verify_token', 'hub_verify_token')
            stored_vt = _clean_hub_str(connector_id.facebook_verify_token)
            # Handshake succeeds when Verify Token matches; do not require connector_type ==
            # facebook (Meta often pings before Odoo saves the type, same UUID may be reused).
            looks_like_verify = hub_mode or hub_challenge or hub_verify
            if hub_mode == 'subscribe' and hub_challenge and hub_verify and stored_vt \
                    and hub_verify == stored_vt:
                return Response(hub_challenge, status=200, headers=[('Content-Type', 'text/plain; charset=utf-8')])
            if looks_like_verify:
                cid = getattr(connector_id, 'uuid', connector_uuid)
                if hub_mode != 'subscribe':
                    _logger.warning(
                        'Messenger webhook verify skipped (wrong hub.mode=%r) connector=%s',
                        hub_mode, cid)
                elif not hub_challenge:
                    _logger.warning(
                        'Messenger webhook verify skipped (missing hub.challenge) connector=%s', cid)
                elif not hub_verify:
                    _logger.warning(
                        'Messenger webhook verify skipped (missing hub.verify_token) connector=%s', cid)
                elif not stored_vt:
                    _logger.warning(
                        'Messenger webhook verify failed: set "Webhook Verify Token" on connector %s '
                        'to the same string as in Meta Dashboard (field is empty).',
                        cid,
                    )
                elif hub_verify != stored_vt:
                    _logger.warning(
                        'Messenger webhook verify failed: token mismatch for connector=%s '
                        '(Meta sent %d chars; Odoo stores %d — must match exactly, case-sensitive).',
                        cid, len(hub_verify), len(stored_vt),
                    )
                return Response(status=403)
            return Response(status=404)

        raw = request.httprequest.get_data(cache=False, as_text=False) or b''

        body_probe = {}
        if raw:
            try:
                body_probe = json.loads(raw.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                body_probe = {}
        messenger_hook = isinstance(body_probe, dict) and body_probe.get('object') == 'page'

        if messenger_hook:
            if connector_id.connector_type != 'facebook':
                _logger.warning(
                    'Messenger webhook POST for connector UUID=%s (type=%s): set Connect to = Facebook '
                    'so outbound/send uses Graph API.',
                    connector_uuid, connector_id.connector_type,
                )

            sig = request.httprequest.headers.get('X-Hub-Signature-256')
            try:
                if not connector_id.facebook_verify_hub_signature256(raw, sig or ''):
                    return Response(status=403)

                jobs = connector_id.facebook_dispatch_webhook(body_probe)

                WorkQueue = request.env['acrux.chat.work.queue'].sudo()
                for job in jobs:
                    WorkQueueData = WorkQueue.create({'ttype': job['ttype'],
                                      'connector_id': connector_id.id,
                                      'data': json.dumps(job['data'], default=str)})
                
                if jobs:
                    WorkQueue.queue_trigger()
                return Response(status=200)
            except Exception:
                request.env.cr.rollback()
                _logger.error('Facebook webhook error', exc_info=True)
                return Response(status=500)

        try:
            payload = {}
            if raw:
                try:
                    body = json.loads(raw.decode(request.httprequest.charset or 'utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return Response(status=400)
                if isinstance(body, dict):
                    inner = body.get('params')
                    payload = inner if isinstance(inner, dict) else body
            updates = payload.get('updates') or []
            events = payload.get('events') or []
            messages = payload.get('messages') or []

            log_request(request)
            if not updates and not events and not messages:
                return Response(status=403)  # Forbidden

            WorkQueue = request.env['acrux.chat.work.queue'].sudo()
            for contact in updates:
                WorkQueue.create({'ttype': 'in_update',
                                  'connector_id': connector_id.id,
                                  'data': json.dumps(contact)})

            for event in events:
                WorkQueue.create({'ttype': 'in_event',
                                  'connector_id': connector_id.id,
                                  'data': json.dumps(event)})

            for mess in messages:
                WorkQueue.create({'ttype': 'in_message',
                                  'connector_id': connector_id.id,
                                  'data': json.dumps(mess)})

            WorkQueue.queue_trigger()
            return Response(status=200)

        except Exception:
            request.env.cr.rollback()
            _logger.error('Error', exc_info=True)
            return Response(status=500)  # Internal Server Error

    @http.route(['/web/chatresource/<int:id>/<string:access_token>',
                 '/web/static/chatresource/<string:model>/<string:id>/<string:field>'],
                type='http', auth='public', sitemap=False)
    def acrux_web_content(self, id=None, model=None, field=None, access_token=None):
        '''
        /web/chatresource/...        -> for attachment
        /web/static/chatresource/... -> for product image
        :param field: field (binary image, PNG or JPG) name in model. Only support 'image'.
        '''

        IrBinary = request.env['ir.binary'].sudo()
        try:
            if id and access_token and not model and not field:
                record = IrBinary._find_record(res_id=int(id), access_token=access_token)
                stream = IrBinary._get_stream_from(record)
            else:
                if not id or not field.startswith('image') or model not in acrux_allowed_models():
                    return Response(status=404)

                id, sep, unique = id.partition('_')
                record = IrBinary._find_record(res_model=model, res_id=int(id))
                stream = IrBinary._get_image_stream_from(record, field_name=field,
                                                         placeholder='web/static/img/XXXXX.png')
        except Exception:
            return Response(status=404)

        response = stream.get_response()
        return response


class Binary(http.Controller):

    @http.route('/web/binary/upload_attachment_chat', methods=['POST'], type='http', auth='user')
    def mail_attachment_upload(self, ufile, is_pending=False, connector_type=None, **kwargs):
        ''' Source: web.controllers.discuss.DiscussController.upload_attachment '''
        if (connector_type == 'instagram' and ufile and ufile.mimetype):
            ufile = self.check_instagram_file(ufile)
        try:
            limit = int(request.env['ir.config_parameter'].sudo().get_param('acrux_max_weight_kb') or '0')
            Attach = request.env['ir.attachment']
            datas = ufile.read()
            if len(datas) > limit * 1024:
                raise UserError(_('Too big, max. %s (%s)') % ('%sMb' % int(limit / 1000), ufile.filename))
            vals = {
                'name': ufile.filename,
                'raw': datas,
                'res_id': 0,
                'res_model': 'acrux.chat.message',
                'delete_old': True,
                'public': True
            }
            if is_pending and is_pending != 'false':
                # Add this point, the message related to the uploaded file does
                # not exist yet, so we use those placeholder values instead.
                vals.update({
                    'res_id': 0,
                    'res_model': 'acrux.chat.message',
                })
            vals['access_token'] = Attach._generate_access_token()
            attachment = Attach.create(vals)
            if ufile.mimetype:
                attachment.mimetype = ufile.mimetype
            attachment._post_add_create()
            attachmentData = {
                'filename': ufile.filename,
                'id': attachment.id,
                'mimetype': attachment.mimetype,
                'name': attachment.name,
                'size': attachment.file_size,
                'isAcrux': True,
            }
            if attachment.access_token:
                attachmentData['accessToken'] = attachment.access_token
        except UserError as e:
            attachmentData = {'error': e.args[0], 'filename': ufile.filename}
            _logger.exception("Fail to upload attachment %s" % ufile.filename)
        except Exception:
            attachmentData = {'error': _("Something horrible happened"), 'filename': ufile.filename}
            _logger.exception("Fail to upload attachment %s" % ufile.filename)
        return request.make_response(
            data=json.dumps(attachmentData),
            headers=[('Content-Type', 'application/json')]
        )

    def check_instagram_file(self, ufile):
        file_type = ufile.mimetype.split('/')[0]
        if (not pydub or file_type not in ['audio', 'video'] or
                ufile.mimetype in INSTAGRAM_AUDIO_FORMAT_ALLOWED or
                ufile.mimetype in INSTAGRAM_VIDEO_FORMAT_ALLOWED):
            return ufile
        data = ufile.read()
        try:
            if file_type == 'audio':
                output_io = self.convert_audio_to_mp4(data)
            else:
                output_io = self.convert_video_to_mp4(data)
            ufile = FileStorage(stream=output_io, filename=f'{file_type}.mp4', content_type=f'{file_type}/mp4')
        except Exception as e:
            _logger.error(e)
            ufile = FileStorage(stream=BytesIO(data), filename=ufile.filename, content_type=ufile.mimetype)
        return ufile

    def convert_audio_to_mp4(self, data):
        file_like = BytesIO(data)
        audio = pydub.AudioSegment.from_file(file_like)
        output_io = BytesIO()
        audio.export(output_io, format='mp4')
        return output_io

    def convert_video_to_mp4(self, data):
        output_io = BytesIO(data)
        encoder = pydub.utils.get_encoder_name()
        if encoder:
            in_file = NamedTemporaryFile(mode='wb', delete=False)
            in_file.write(data)
            in_file.seek(0)
            output = NamedTemporaryFile(mode='w+b', delete=False)
            conversion_command = [
                encoder, '-y', in_file.name,
                '-acodec', 'aac',
                '-vcodec', 'libx264',
                '-f', 'mp4', output.name
            ]
            with open(os.devnull, 'rb') as devnull:
                p = subprocess.Popen(conversion_command, stdin=devnull, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                _p_out, p_err = p.communicate()
            if p.returncode != 0:
                in_file.close()
                output.close()
                raise Exception(p_err.decode(errors='ignore'))
            output.seek(0)
            output_io = BytesIO(output.read())
            output.close()
            in_file.close()
        return output_io
