# -*- coding: utf-8 -*-
"""Google Drive storage for event snapshots, event clips, logs and backups.

Auth is OAuth 2.0 (the Gmail owner signs in on Google's own page once; Odoo keeps only a refresh
token). A Gmail password can NOT be used with the Drive API, so it is never asked for or stored.
Scope: drive.file -> Odoo can only see the files/folders it created itself.
"""
import base64
import json
import logging
import re
import time
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
FILES_URL = 'https://www.googleapis.com/drive/v3/files'
UPLOAD_URL = 'https://www.googleapis.com/upload/drive/v3/files'
SCOPES = 'https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/userinfo.email'
CHUNK = 8 * 1024 * 1024           # must be a multiple of 256 KiB
SIMPLE_LIMIT = 5 * 1024 * 1024


def _safe(name):
    """Drive allows nearly anything, but keep folder names tidy and path-safe."""
    return re.sub(r'[\\/:*?"<>|]+', '-', (name or 'unnamed')).strip() or 'unnamed'


class CctvDriveFolder(models.Model):
    """Cache: folder path -> Drive folder id (so we do not search Drive for every upload)."""
    _name = 'cctv.drive.folder'
    _description = 'CCTV Google Drive Folder Cache'

    path = fields.Char(required=True, index=True)
    drive_id = fields.Char(required=True)

    _sql_constraints = [('path_uniq', 'unique(path)', 'Folder path already cached.')]


class CctvGdrive(models.AbstractModel):
    _name = 'cctv.gdrive'
    _description = 'CCTV Google Drive client'

    # ------------------------------------------------------------------ settings access
    @api.model
    def _param(self, key, default=''):
        return self.env['ir.config_parameter'].sudo().get_param('cctv_management.' + key, default) or default

    @api.model
    def _set_param(self, key, value):
        self.env['ir.config_parameter'].sudo().set_param('cctv_management.' + key, value or '')

    @api.model
    def is_connected(self):
        return bool(self._param('gdrive_refresh_token'))

    @api.model
    def redirect_uri(self):
        base = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')
        return base + '/cctv/gdrive/callback'

    # ------------------------------------------------------------------ OAuth
    @api.model
    def auth_url(self, state):
        client_id = self._param('gdrive_client_id')
        if not client_id or not self._param('gdrive_client_secret'):
            raise UserError(_('Enter the Google OAuth Client ID and Client Secret first (CCTV > Configuration > '
                              'Settings > Google Drive), then press Save, then Connect.'))
        from urllib.parse import urlencode
        return AUTH_URL + '?' + urlencode({
            'client_id': client_id, 'redirect_uri': self.redirect_uri(), 'response_type': 'code',
            'scope': SCOPES, 'access_type': 'offline', 'prompt': 'consent', 'state': state,
            'include_granted_scopes': 'true',
        })

    @api.model
    def exchange_code(self, code):
        r = requests.post(TOKEN_URL, data={
            'code': code, 'client_id': self._param('gdrive_client_id'),
            'client_secret': self._param('gdrive_client_secret'),
            'redirect_uri': self.redirect_uri(), 'grant_type': 'authorization_code'}, timeout=20)
        data = r.json() if r.content else {}
        if r.status_code != 200 or not data.get('refresh_token'):
            raise UserError(_('Google did not return a refresh token: %s')
                            % (data.get('error_description') or data.get('error') or r.text[:200]))
        self._set_param('gdrive_refresh_token', data['refresh_token'])
        self._cache_token(data)
        try:
            u = requests.get(USERINFO_URL, headers={'Authorization': 'Bearer ' + data['access_token']}, timeout=15)
            self._set_param('gdrive_email', (u.json() or {}).get('email', ''))
        except requests.RequestException:
            pass
        self._set_param('gdrive_connected_on', fields.Datetime.to_string(fields.Datetime.now()))
        return True

    @api.model
    def disconnect(self):
        token = self._param('gdrive_refresh_token')
        if token:
            try:
                requests.post('https://oauth2.googleapis.com/revoke', data={'token': token}, timeout=10)
            except requests.RequestException:
                pass
        for key in ('gdrive_refresh_token', 'gdrive_access_token', 'gdrive_token_expiry', 'gdrive_email',
                    'gdrive_root_folder_id', 'gdrive_connected_on'):
            self._set_param(key, '')
        self.env['cctv.drive.folder'].sudo().search([]).unlink()

    @api.model
    def _cache_token(self, data):
        self._set_param('gdrive_access_token', data.get('access_token'))
        self._set_param('gdrive_token_expiry', str(int(time.time()) + int(data.get('expires_in', 3600)) - 60))

    @api.model
    def _access_token(self, force=False):
        if not self.is_connected():
            raise UserError(_('Google Drive is not connected.'))
        if not force and self._param('gdrive_access_token') and int(self._param('gdrive_token_expiry', 0) or 0) > time.time():
            return self._param('gdrive_access_token')
        r = requests.post(TOKEN_URL, data={
            'client_id': self._param('gdrive_client_id'), 'client_secret': self._param('gdrive_client_secret'),
            'refresh_token': self._param('gdrive_refresh_token'), 'grant_type': 'refresh_token'}, timeout=20)
        data = r.json() if r.content else {}
        if r.status_code != 200:
            raise UserError(_('Google refused to renew access (%s). Reconnect Google Drive in Settings. '
                              'If the OAuth app is still in "Testing" mode, tokens expire after 7 days: '
                              'publish the app.') % (data.get('error_description') or data.get('error') or r.status_code))
        self._cache_token(data)
        return data['access_token']

    # ------------------------------------------------------------------ HTTP
    @api.model
    def _call(self, method, url, **kw):
        kw.setdefault('timeout', 60)
        headers = dict(kw.pop('headers', {}))
        for attempt in (1, 2):
            headers['Authorization'] = 'Bearer ' + self._access_token(force=attempt == 2)
            try:
                r = requests.request(method, url, headers=headers, **kw)
            except requests.RequestException as exc:
                raise UserError(_('Cannot reach Google Drive: %s') % exc)
            if r.status_code == 401 and attempt == 1:
                continue
            break
        if r.status_code >= 400:
            try:
                msg = r.json()['error']['message']
            except Exception:
                msg = r.text[:200]
            raise UserError(_('Google Drive error %s: %s') % (r.status_code, msg))
        return r

    # ------------------------------------------------------------------ folders
    @api.model
    def _find_or_create_folder(self, name, parent_id=None):
        q = "mimeType='application/vnd.google-apps.folder' and trashed=false and name='%s'" % name.replace("'", "\\'")
        q += " and '%s' in parents" % (parent_id or 'root')
        r = self._call('GET', FILES_URL, params={'q': q, 'fields': 'files(id,name)', 'pageSize': 1})
        files = r.json().get('files') or []
        if files:
            return files[0]['id']
        body = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_id:
            body['parents'] = [parent_id]
        r = self._call('POST', FILES_URL, params={'fields': 'id'}, json=body)
        return r.json()['id']

    @api.model
    def ensure_path(self, parts):
        """Create (or reuse) nested folders and return the id of the last one."""
        Folder = self.env['cctv.drive.folder'].sudo()
        parent, built = None, []
        for part in parts:
            built.append(_safe(part))
            key = '/'.join(built)
            cached = Folder.search([('path', '=', key)], limit=1)
            if cached:
                parent = cached.drive_id
                continue
            parent = self._find_or_create_folder(_safe(part), parent)
            Folder.create({'path': key, 'drive_id': parent})
        return parent

    @api.model
    def root_name(self):
        return self._param('gdrive_root_name', 'CCTV')

    @api.model
    def camera_folder_parts(self, cam):
        return [self.root_name(), cam.office_id.name or 'No Site', '%s - %s' % (cam.camera_code, cam.name)]

    @api.model
    def camera_folder_id(self, cam):
        return self.ensure_path(self.camera_folder_parts(cam))

    # ------------------------------------------------------------------ upload / delete
    @api.model
    def upload_bytes(self, name, data, mimetype, folder_id):
        size = len(data)
        if size <= SIMPLE_LIMIT:
            meta = json.dumps({'name': name, 'parents': [folder_id]})
            boundary = 'cctvboundary%d' % int(time.time() * 1000)
            body = (('--%s\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n%s\r\n--%s\r\nContent-Type: %s\r\n\r\n'
                     % (boundary, meta, boundary, mimetype)).encode() + data + ('\r\n--%s--' % boundary).encode())
            r = self._call('POST', UPLOAD_URL, params={'uploadType': 'multipart', 'fields': 'id,webViewLink'},
                           data=body, headers={'Content-Type': 'multipart/related; boundary=%s' % boundary},
                           timeout=120)
            return r.json()
        return self.upload_stream(name, size, lambda off, n: data[off:off + n], mimetype, folder_id)

    @api.model
    def upload_stream(self, name, size, reader, mimetype, folder_id):
        """Resumable upload; reader(offset, length) -> bytes. Used for clips > 5 MB and DB backups."""
        r = self._call('POST', UPLOAD_URL, params={'uploadType': 'resumable', 'fields': 'id,webViewLink'},
                       json={'name': name, 'parents': [folder_id]},
                       headers={'X-Upload-Content-Type': mimetype, 'X-Upload-Content-Length': str(size)})
        session = r.headers.get('Location')
        if not session:
            raise UserError(_('Google Drive did not open an upload session.'))
        offset = 0
        while offset < size or size == 0:
            chunk = reader(offset, CHUNK)
            end = offset + len(chunk) - 1
            headers = {'Content-Length': str(len(chunk)),
                       'Content-Range': 'bytes %d-%d/%d' % (offset, end, size) if chunk else 'bytes */%d' % size}
            resp = requests.put(session, data=chunk, headers=headers, timeout=300)
            if resp.status_code in (200, 201):
                return resp.json()
            if resp.status_code != 308:
                raise UserError(_('Drive upload failed (%s): %s') % (resp.status_code, resp.text[:200]))
            offset += len(chunk)
            if not chunk:
                break
        raise UserError(_('Drive upload ended without a confirmation.'))

    @api.model
    def delete_file(self, file_id):
        try:
            self._call('DELETE', '%s/%s' % (FILES_URL, file_id))
        except UserError as exc:
            if '404' not in str(exc):          # already gone is fine
                raise

    @api.model
    def test_connection(self):
        root = self.ensure_path([self.root_name()])
        self._set_param('gdrive_root_folder_id', root)
        return root
