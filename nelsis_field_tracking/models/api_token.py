import hashlib
import secrets
from datetime import timedelta

from odoo import api, fields, models


class NelsisApiToken(models.Model):
    _name = 'nelsis.api.token'
    _description = 'Mobile App Session Token'
    _order = 'id desc'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    token_hash = fields.Char(required=True, index=True, readonly=True)
    device_uid = fields.Char(string='Device ID')
    device_name = fields.Char()
    platform = fields.Selection([('android', 'Android'), ('ios', 'iOS'), ('other', 'Other')], default='other')
    app_version = fields.Char()
    fcm_token = fields.Char(string='Push Token')
    last_ip = fields.Char()
    last_used = fields.Datetime()
    expires_at = fields.Datetime(required=True)
    revoked = fields.Boolean(default=False)
    active = fields.Boolean(default=True)

    _sql_constraints = [('token_hash_uniq', 'unique(token_hash)', 'Token collision.')]

    @staticmethod
    def _hash(raw):
        return hashlib.sha256(raw.encode()).hexdigest()

    @api.model
    def issue(self, user, device=None, ip=None):
        """Create a session and return the raw token (it is never stored)."""
        device = device or {}
        raw = secrets.token_urlsafe(48)
        days = self.env['nelsis.config'].int_param('nelsis.token_days')
        # one active session per physical device
        if device.get('uid'):
            self.sudo().search([('user_id', '=', user.id), ('device_uid', '=', device['uid'])]).write(
                {'revoked': True, 'active': False})
        platform = device.get('platform')
        self.sudo().create({
            'user_id': user.id,
            'token_hash': self._hash(raw),
            'device_uid': device.get('uid'),
            'device_name': device.get('name'),
            'platform': platform if platform in ('android', 'ios') else 'other',
            'app_version': device.get('app_version'),
            'fcm_token': device.get('fcm_token'),
            'last_ip': ip,
            'last_used': fields.Datetime.now(),
            'expires_at': fields.Datetime.now() + timedelta(days=days),
        })
        return raw

    @api.model
    def verify(self, raw, ip=None):
        """Return the res.users record for a valid bearer token, else None."""
        if not raw:
            return None
        rec = self.sudo().search([('token_hash', '=', self._hash(raw)), ('revoked', '=', False)], limit=1)
        if not rec or rec.expires_at < fields.Datetime.now() or not rec.user_id.active:
            return None
        now = fields.Datetime.now()
        if not rec.last_used or (now - rec.last_used).total_seconds() > 60:
            vals = {'last_used': now, 'last_ip': ip}
            # Sliding session: an employee who uses the app is not logged out every N days, while an
            # abandoned device still expires N days after its last use.
            days = self.env['nelsis.config'].int_param('nelsis.token_days')
            if (rec.expires_at - now).total_seconds() < days * 86400 - 86400:
                vals['expires_at'] = now + timedelta(days=days)
            rec.write(vals)
        return rec.user_id

    @api.model
    def set_push_token(self, raw, fcm_token):
        """Remember the phone's Firebase token for this session (one phone = one row)."""
        rec = self.sudo().search([('token_hash', '=', self._hash(raw)), ('revoked', '=', False)], limit=1)
        if not rec:
            return False
        fcm_token = (fcm_token or '').strip()[:4096] or False
        if fcm_token:  # the same phone token must not stay on an older / other user's session
            self.sudo().search([('fcm_token', '=', fcm_token), ('id', '!=', rec.id)]).write({'fcm_token': False})
        rec.fcm_token = fcm_token
        return True

    @api.model
    def revoke(self, raw):
        self.sudo().search([('token_hash', '=', self._hash(raw))]).write({'revoked': True, 'active': False})

    def action_revoke(self):
        self.write({'revoked': True, 'active': False})

    @api.model
    def _cron_gc(self):
        limit = fields.Datetime.now() - timedelta(days=7)
        self.sudo().with_context(active_test=False).search(
            ['|', ('expires_at', '<', limit), '&', ('revoked', '=', True), ('write_date', '<', limit)]).unlink()
