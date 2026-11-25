from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nelsis_google_maps_key = fields.Char(string='Google Maps API Key', config_parameter='nelsis.google_maps_key')
    nelsis_track_interval_sec = fields.Integer(string='Tracking Interval (s)', config_parameter='nelsis.track_interval_sec', default=60)
    nelsis_track_distance_m = fields.Integer(string='Min. Movement (m)', config_parameter='nelsis.track_distance_m', default=25)
    nelsis_geofence_mode = fields.Selection(
        [('off', 'Off'), ('warn', 'Warn only (flag in reports)'), ('block', 'Block punch outside site')],
        string='Geofence Mode', config_parameter='nelsis.geofence_mode', default='warn')
    nelsis_max_accuracy_m = fields.Integer(string='Max. GPS Error (m)', config_parameter='nelsis.max_accuracy_m', default=100)
    nelsis_stale_minutes = fields.Integer(string='Offline After (min)', config_parameter='nelsis.stale_minutes', default=5)
    nelsis_time_tolerance_sec = fields.Integer(string='Clock Tolerance (s)', config_parameter='nelsis.time_tolerance_sec', default=300)
    nelsis_retention_days = fields.Integer(string='Keep Tracking Data (days)', config_parameter='nelsis.retention_days', default=180)
    nelsis_require_photo_punch = fields.Boolean(string='Selfie Required on Punch', config_parameter='nelsis.require_photo_punch', default=True)
    nelsis_block_mock = fields.Boolean(string='Block Mock GPS', config_parameter='nelsis.block_mock', default=True)
    nelsis_token_days = fields.Integer(string='App Session (days)', config_parameter='nelsis.token_days', default=30)
    nelsis_fcm_project_note = fields.Char(string='Firebase project', compute='_compute_fcm_project_note')
    nelsis_fcm_api_key = fields.Char(string='Firebase API Key', config_parameter='nelsis.fcm_api_key')
    nelsis_fcm_app_id = fields.Char(string='Firebase App ID', config_parameter='nelsis.fcm_app_id')
    nelsis_fcm_sender_id = fields.Char(string='Firebase Sender ID', config_parameter='nelsis.fcm_sender_id')
    nelsis_fcm_service_account = fields.Text(string='Service account JSON', config_parameter='nelsis.fcm_service_account')

    def _compute_fcm_project_note(self):
        pid = self.env['nelsis.fcm'].project_id()
        for rec in self:
            rec.nelsis_fcm_project_note = pid or 'Not configured'
