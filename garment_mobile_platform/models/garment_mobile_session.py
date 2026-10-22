# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentMobileSession(models.Model):
    """Mobile Login/Session Audit (SRS s.20 Mobile Security, s.23
    Authentication System, s.39 Mobile API Security, s.52 Active Sessions /
    Remote Logout) — garment.mobile.session. One record is created by
    /api/mobile/auth/login on every successful login."""
    _name = 'garment.mobile.session'
    _description = 'Garment Mobile Session'
    _inherit = ['mail.thread']
    _order = 'login_datetime desc'

    session_number = fields.Char(string='Session No.', copy=False, readonly=True, default=lambda s: _('New'))
    device_id = fields.Many2one('garment.mobile.device', string='Device', required=True,
                                 ondelete='cascade', tracking=True)
    user_id = fields.Many2one('res.users', string='User', required=True, tracking=True)
    app_type = fields.Selection(related='device_id.app_type', string='Mobile App', store=True)

    login_method = fields.Selection([
        ('password', 'Username & Password'),
        ('otp_mobile', 'Mobile Number OTP'),
        ('otp_email', 'Email OTP'),
        ('biometric', 'Biometric'),
    ], string='Login Method', default='password', required=True)

    login_datetime = fields.Datetime(string='Login At', default=fields.Datetime.now, required=True)
    logout_datetime = fields.Datetime(string='Logout At')
    ip_address = fields.Char(string='IP Address')
    duration_minutes = fields.Float(string='Duration (minutes)', compute='_compute_duration', store=True)

    status = fields.Selection([
        ('active', 'Active'), ('closed', 'Closed'), ('expired', 'Expired'),
    ], string='Status', default='active', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    @api.depends('login_datetime', 'logout_datetime')
    def _compute_duration(self):
        for rec in self:
            if rec.login_datetime and rec.logout_datetime:
                delta = rec.logout_datetime - rec.login_datetime
                rec.duration_minutes = round(delta.total_seconds() / 60.0, 2)
            else:
                rec.duration_minutes = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('session_number', _('New')) == _('New'):
                vals['session_number'] = self.env['ir.sequence'].next_by_code('garment.mobile.session') or _('New')
        return super().create(vals_list)

    def action_close_session(self):
        """Remote Logout (SRS s.52)."""
        self.write({'status': 'closed', 'logout_datetime': fields.Datetime.now()})

    def action_expire_session(self):
        self.write({'status': 'expired', 'logout_datetime': fields.Datetime.now()})
