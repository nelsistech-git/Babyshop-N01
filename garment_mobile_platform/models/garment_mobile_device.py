# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

import secrets

from odoo import api, fields, models, _


class GarmentMobileDevice(models.Model):
    """Mobile Device Registry (SRS s.36-38, s.52 — Mobile Database Models /
    Mobile Device Management) — garment.mobile.device. One record per
    Android/iOS/PWA device registered by an ERP user. Carries the generated
    API key used by the pragmatic API-key auth scheme in
    ``controllers/main.py`` (see IMPLEMENTATION_NOTES.md for why a full
    JWT/OAuth2 server is out of scope here)."""
    _name = 'garment.mobile.device'
    _description = 'Garment Mobile Device'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'last_seen desc, id desc'
    _rec_name = 'name'

    device_code = fields.Char(string='Device Code', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Device Name', required=True, tracking=True,
                        help='Friendly label, e.g. "Samsung Galaxy S25 - Line Supervisor".')

    user_id = fields.Many2one('res.users', string='ERP User', required=True, tracking=True, ondelete='cascade')
    employee_id = fields.Many2one('garment.hr.employee', string='Employee',
                                   help='Optional link when the device belongs to a factory worker/staff '
                                        'tracked in garment_hr.')

    app_type = fields.Selection([
        ('executive', 'Executive Mobile App'),
        ('employee_ess', 'Employee Self Service App'),
        ('merchandising', 'Merchandising App'),
        ('production', 'Production App'),
        ('quality', 'Quality Control App'),
        ('warehouse', 'Warehouse App'),
        ('hr', 'HR App'),
        ('finance', 'Finance Approval App'),
    ], string='Mobile App', required=True, default='production', tracking=True,
        help='Which of the SRS s.5 application areas this device is registered for.')

    platform = fields.Selection([
        ('android', 'Android'), ('ios', 'iOS'), ('web_pwa', 'Web / PWA'),
    ], string='Platform', required=True, default='android')
    device_identifier = fields.Char(string='Device Identifier',
                                     help='Client-generated UUID / IMEI used to recognise this device on re-login.')
    device_model = fields.Char(string='Device Model', help='e.g. Samsung Galaxy S25, iPhone 15')
    os_version = fields.Char(string='OS Version')
    app_version = fields.Char(string='App Version')

    push_token = fields.Char(string='Push Token', help='FCM (Android) or APNs (iOS) device push token.')
    push_provider = fields.Selection([
        ('fcm', 'Firebase Cloud Messaging'), ('apns', 'Apple Push Notification Service'), ('none', 'Not Set'),
    ], string='Push Provider', compute='_compute_push_provider', store=True)

    api_key = fields.Char(string='API Key', copy=False, readonly=True,
                           help='Generated on registration. Sent by the mobile client as the '
                                'X-Mobile-Api-Key header (or api_key body field) on every '
                                '/api/mobile/... call. See controllers/main.py.')

    status = fields.Selection([
        ('active', 'Active'), ('blocked', 'Blocked'), ('inactive', 'Inactive'),
    ], string='Status', default='active', tracking=True)

    registered_date = fields.Datetime(string='Registered On', default=fields.Datetime.now, readonly=True)
    last_login = fields.Datetime(string='Last Login')
    last_seen = fields.Datetime(string='Last Seen')
    last_ip = fields.Char(string='Last IP Address')

    session_ids = fields.One2many('garment.mobile.session', 'device_id', string='Sessions')
    notification_ids = fields.One2many('garment.mobile.push.notification', 'device_id', string='Notifications')
    sync_log_ids = fields.One2many('garment.mobile.offline.sync.log', 'device_id', string='Offline Sync Log')
    session_count = fields.Integer(compute='_compute_counts')
    sync_log_count = fields.Integer(compute='_compute_counts')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('device_code_uniq', 'unique(device_code, company_id)', 'Device Code must be unique per company!'),
        ('api_key_uniq', 'unique(api_key)', 'API Key must be unique!'),
    ]

    @api.depends('platform')
    def _compute_push_provider(self):
        for rec in self:
            if rec.platform == 'android':
                rec.push_provider = 'fcm'
            elif rec.platform == 'ios':
                rec.push_provider = 'apns'
            else:
                rec.push_provider = 'none'

    @api.depends('session_ids', 'sync_log_ids')
    def _compute_counts(self):
        for rec in self:
            rec.session_count = len(rec.session_ids)
            rec.sync_log_count = len(rec.sync_log_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('device_code', _('New')) == _('New'):
                vals['device_code'] = self.env['ir.sequence'].next_by_code('garment.mobile.device') or _('New')
            if not vals.get('api_key'):
                vals['api_key'] = self._generate_api_key()
        return super().create(vals_list)

    @api.model
    def _generate_api_key(self):
        return secrets.token_hex(24)

    def action_generate_api_key(self):
        """Rotate the API key — any client using the old key must re-login."""
        for rec in self:
            rec.api_key = self._generate_api_key()

    def action_block(self):
        self.write({'status': 'blocked'})

    def action_activate(self):
        self.write({'status': 'active'})

    def action_view_sessions(self):
        self.ensure_one()
        return {
            'name': _('Sessions'), 'type': 'ir.actions.act_window', 'res_model': 'garment.mobile.session',
            'view_mode': 'tree,form', 'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
        }

    def action_view_sync_logs(self):
        self.ensure_one()
        return {
            'name': _('Offline Sync Log'), 'type': 'ir.actions.act_window',
            'res_model': 'garment.mobile.offline.sync.log',
            'view_mode': 'tree,form', 'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
        }

    def touch(self):
        """Called by the API controllers on every authenticated request to
        refresh last_seen without generating chatter noise."""
        self.sudo().write({'last_seen': fields.Datetime.now()})
