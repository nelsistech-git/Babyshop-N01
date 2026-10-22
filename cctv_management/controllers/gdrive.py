# -*- coding: utf-8 -*-
"""Google Drive OAuth sign-in. The Gmail owner logs in on Google's page; Odoo never sees the password."""
import logging
import time

from odoo import http, tools
from odoo.http import request

_logger = logging.getLogger(__name__)
_PAGE = ('<html><body style="font-family:sans-serif;max-width:560px;margin:60px auto">'
         '<h2>%s</h2><p>%s</p><p><a href="/web#action=cctv_management.action_cctv_settings">'
         'Back to CCTV settings</a></p></body></html>')


def _is_admin():
    return request.env.user.has_group('base.group_system')


def _sign(uid, ts):
    return tools.misc.hmac(request.env(su=True), 'cctv_gdrive_state', '%s:%s' % (uid, ts))


class CctvGdriveController(http.Controller):

    @http.route('/cctv/gdrive/connect', type='http', auth='user')
    def connect(self, **kw):
        if not _is_admin():
            return request.make_response(_PAGE % ('Not allowed', 'Only an Odoo administrator can connect Google Drive.'))
        ts = int(time.time())
        state = '%s:%s:%s' % (request.env.uid, ts, _sign(request.env.uid, ts))
        try:
            url = request.env['cctv.gdrive'].auth_url(state)
        except Exception as exc:
            return request.make_response(_PAGE % ('Cannot start Google sign-in', str(exc)))
        return request.redirect(url, local=False)

    @http.route('/cctv/gdrive/callback', type='http', auth='user')
    def callback(self, code=None, state=None, error=None, **kw):
        if not _is_admin():
            return request.make_response(_PAGE % ('Not allowed', 'Only an Odoo administrator can connect Google Drive.'))
        if error or not code:
            return request.make_response(_PAGE % ('Google sign-in was cancelled', error or 'No authorisation code.'))
        try:
            uid, ts, sig = (state or '').split(':', 2)
            valid = (int(uid) == request.env.uid and time.time() - int(ts) < 900
                     and tools.misc.consteq(sig, _sign(uid, ts)))
        except (ValueError, TypeError):
            valid = False
        if not valid:
            return request.make_response(_PAGE % ('Sign-in link expired', 'Start again from CCTV > Configuration > Settings.'))
        env = request.env
        try:
            drive = env['cctv.gdrive']
            drive.exchange_code(code)
            drive.test_connection()
            env['cctv.camera'].refresh_storage_locations()
        except Exception as exc:
            _logger.exception('gdrive callback failed')
            return request.make_response(_PAGE % ('Connecting Google Drive failed', str(exc)))
        return request.make_response(_PAGE % ('Google Drive connected',
                                              'Snapshots, clips, logs and backups will now be stored in your Drive.'))
