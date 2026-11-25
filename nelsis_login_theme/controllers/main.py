# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request


class NelsisLoginThemeController(http.Controller):
    """Streams the configured logo / image / video / powered-by image to the
    public login page without ever exposing ORM access to the settings
    model: every lookup goes through ``sudo()`` on a single whitelisted
    field name.
    """

    _FIELD_KIND = {
        'company_logo': 'image',
        'media_image': 'image',
        'media_video': 'video',
        'background_image': 'image',
        'powered_by_image': 'image',
    }

    @staticmethod
    def _guess_image_mimetype(data):
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image/png'
        if data[:3] == b'\xff\xd8\xff':
            return 'image/jpeg'
        if data[:6] in (b'GIF87a', b'GIF89a'):
            return 'image/gif'
        if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return 'image/webp'
        if data[:5] == b'<?xml' or data[:4] == b'<svg':
            return 'image/svg+xml'
        return 'image/png'

    @staticmethod
    def _guess_video_mimetype(data):
        if data[:4] == b'\x1a\x45\xdf\xa3':
            return 'video/webm'
        return 'video/mp4'

    @http.route(
        ['/nelsis_login_theme/media/<string:field>'],
        type='http', auth='public', csrf=False, methods=['GET'],
    )
    def media(self, field, **kw):
        kind = self._FIELD_KIND.get(field)
        if not kind:
            return request.not_found()

        config = request.env['login.theme.config'].sudo().get_config()
        data_b64 = getattr(config, field, False)
        if not data_b64:
            return request.not_found()

        try:
            content = base64.b64decode(data_b64)
        except Exception:
            return request.not_found()

        if not content:
            return request.not_found()

        mimetype = (
            self._guess_video_mimetype(content)
            if kind == 'video' else self._guess_image_mimetype(content)
        )
        headers = [
            ('Content-Type', mimetype),
            ('Content-Length', len(content)),
            ('Cache-Control', 'public, max-age=3600'),
        ]
        return request.make_response(content, headers=headers)
