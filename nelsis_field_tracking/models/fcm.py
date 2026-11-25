"""Minimal Firebase Cloud Messaging (HTTP v1) sender - no extra Python packages needed.

Uses a Google service-account JSON key (Firebase console > Project settings > Service accounts > Generate new
private key). The RS256 signature is made with `cryptography`, which Odoo already depends on.
"""
import base64
import json
import logging
import time

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo import api, models

_logger = logging.getLogger(__name__)
SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
_CACHE = {}


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=')


class NelsisFcm(models.AbstractModel):
    _name = 'nelsis.fcm'
    _description = 'Firebase Cloud Messaging sender'

    @api.model
    def _credentials(self):
        raw = self.env['ir.config_parameter'].sudo().get_param('nelsis.fcm_service_account') or ''
        try:
            cred = json.loads(raw)
        except ValueError:
            return None
        need = ('client_email', 'private_key', 'project_id')
        return cred if isinstance(cred, dict) and all(cred.get(k) for k in need) else None

    @api.model
    def configured(self):
        return bool(self._credentials())

    @api.model
    def project_id(self):
        cred = self._credentials()
        return cred['project_id'] if cred else ''

    @api.model
    def _access_token(self, cred):
        cached = _CACHE.get(cred['client_email'])
        if cached and cached[1] > time.time() + 60:
            return cached[0]
        now = int(time.time())
        uri = cred.get('token_uri') or 'https://oauth2.googleapis.com/token'
        head = _b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode())
        claim = _b64(json.dumps({'iss': cred['client_email'], 'scope': SCOPE, 'aud': uri,
                                 'iat': now, 'exp': now + 3600}).encode())
        signing_input = head + b'.' + claim
        key = serialization.load_pem_private_key(cred['private_key'].encode(), password=None)
        signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        assertion = (signing_input + b'.' + _b64(signature)).decode()
        resp = requests.post(uri, data={'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                                        'assertion': assertion}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        _CACHE[cred['client_email']] = (data['access_token'], now + int(data.get('expires_in', 3600)))
        return data['access_token']

    @api.model
    def send(self, token, title, body, data=None):
        """-> 'ok' | 'invalid' (token is dead, remove it) | an error text."""
        cred = self._credentials()
        if not cred:
            return 'Firebase is not configured.'
        try:
            access = self._access_token(cred)
            message = {
                'token': token,
                'notification': {'title': title[:200], 'body': body[:1500]},
                'data': {k: str(v) for k, v in (data or {}).items()},
                'android': {'priority': 'HIGH', 'notification': {'channel_id': 'nelsis_announcements'}},
                'apns': {'payload': {'aps': {'sound': 'default'}}},
            }
            resp = requests.post(
                'https://fcm.googleapis.com/v1/projects/%s/messages:send' % cred['project_id'],
                headers={'Authorization': 'Bearer ' + access}, json={'message': message}, timeout=15)
        except Exception as e:  # noqa: BLE001
            _logger.warning('FCM request failed: %s', e)
            return 'FCM request failed: %s' % str(e)[:200]
        if resp.status_code == 200:
            return 'ok'
        if resp.status_code == 404 or '"UNREGISTERED"' in resp.text or 'registration-token-not-registered' in resp.text:
            return 'invalid'
        return 'FCM %s: %s' % (resp.status_code, resp.text[:200])
