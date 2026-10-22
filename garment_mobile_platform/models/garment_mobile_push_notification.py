# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class GarmentMobilePushNotification(models.Model):
    """Push Notification Log/Queue (SRS s.26 — Push Notification System,
    s.51 GET /api/notifications) — garment.mobile.push.notification.

    NOTE — INTEGRATION STUB: this model is a real, working notification
    log/queue (create, list via /api/mobile/notifications, mark read). The
    actual outbound push call to Firebase Cloud Messaging (Android) / Apple
    Push Notification Service (iOS) is NOT implemented — it requires
    external provider credentials (FCM server key / APNs certificate) that
    this environment does not have. ``_send_via_fcm`` / ``_send_via_apns``
    below are clearly marked TODO stubs. See IMPLEMENTATION_NOTES.md."""
    _name = 'garment.mobile.push.notification'
    _description = 'Garment Mobile Push Notification'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    notification_number = fields.Char(string='Notification No.', copy=False, readonly=True,
                                       default=lambda s: _('New'))
    device_id = fields.Many2one('garment.mobile.device', string='Device',
                                 help='Leave blank to fan this out to every active device of user_id.')
    user_id = fields.Many2one('res.users', string='Recipient User', required=True, tracking=True)

    notification_type = fields.Selection([
        ('management_alert', 'Management Alert'),
        ('production_alert', 'Production Alert'),
        ('quality_alert', 'Quality Alert'),
        ('maintenance_alert', 'Maintenance Alert'),
        ('approval', 'Approval Request'),
        ('attendance', 'Attendance Alert'),
        ('tna', 'TNA / Shipment Alert'),
        ('general', 'General / Company Notice'),
    ], string='Notification Type', required=True, default='general', tracking=True)

    title = fields.Char(string='Title', required=True)
    body = fields.Text(string='Message')

    related_model = fields.Char(string='Related Model',
                                 help='Technical model name of the record this alert is about, '
                                      'e.g. garment.production.entry.')
    related_res_id = fields.Integer(string='Related Record ID')

    push_provider = fields.Selection([
        ('fcm', 'Firebase Cloud Messaging'), ('apns', 'Apple Push Notification Service'), ('none', 'Not Set'),
    ], string='Push Provider', default='none')

    state = fields.Selection([
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ], string='Status', default='queued', tracking=True)

    scheduled_date = fields.Datetime(string='Scheduled/Created', default=fields.Datetime.now)
    sent_date = fields.Datetime(string='Sent On')
    read_date = fields.Datetime(string='Read On')
    error_message = fields.Text(string='Error Message', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('notification_number', _('New')) == _('New'):
                vals['notification_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.mobile.push.notification') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Delivery — TODO integration point (see class docstring).
    # ------------------------------------------------------------------
    def action_send(self):
        """Attempt delivery. Currently always resolves to the documented
        stub below — no real FCM/APNs call is made in this environment."""
        for rec in self:
            try:
                if rec.device_id and rec.device_id.platform == 'ios':
                    rec._send_via_apns()
                else:
                    rec._send_via_fcm()
                rec.write({'state': 'sent', 'sent_date': fields.Datetime.now(), 'error_message': False})
            except NotImplementedError as exc:
                _logger.info('Mobile push delivery not configured for notification %s: %s',
                              rec.notification_number, exc)
                rec.write({'state': 'failed', 'error_message': str(exc)})

    def _send_via_fcm(self):
        """TODO: call the Firebase Cloud Messaging HTTP v1 API here using a
        service-account key stored in ir.config_parameter
        (e.g. garment_mobile_platform.fcm_service_account_json) and
        self.device_id.push_token as the target. Not implemented — no FCM
        credentials are available in this environment."""
        self.ensure_one()
        raise NotImplementedError(_(
            'FCM push delivery is not configured. Add Firebase service-account credentials '
            'and implement the HTTP v1 send call in _send_via_fcm() (see IMPLEMENTATION_NOTES.md).'))

    def _send_via_apns(self):
        """TODO: call Apple Push Notification Service (APNs HTTP/2 API)
        here using a .p8 auth key / certificate stored in
        ir.config_parameter and self.device_id.push_token as the device
        token. Not implemented — no APNs credentials are available in this
        environment."""
        self.ensure_one()
        raise NotImplementedError(_(
            'APNs push delivery is not configured. Add an APNs auth key/certificate '
            'and implement the HTTP/2 send call in _send_via_apns() (see IMPLEMENTATION_NOTES.md).'))

    def action_mark_read(self):
        self.write({'state': 'read', 'read_date': fields.Datetime.now()})
