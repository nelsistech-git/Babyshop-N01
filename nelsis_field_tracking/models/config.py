from odoo import api, models

DEFAULTS = {
    'nelsis.google_maps_key': '',
    'nelsis.track_interval_sec': '60',
    'nelsis.track_distance_m': '25',
    'nelsis.geofence_mode': 'warn',          # off | warn | block
    'nelsis.max_accuracy_m': '100',
    'nelsis.stale_minutes': '5',
    'nelsis.time_tolerance_sec': '300',
    'nelsis.retention_days': '180',
    'nelsis.require_photo_punch': '1',
    'nelsis.block_mock': '1',
    'nelsis.token_days': '30',
    'nelsis.fcm_api_key': '',
    'nelsis.fcm_app_id': '',
    'nelsis.fcm_sender_id': '',
    'nelsis.fcm_service_account': '',
}


class NelsisConfig(models.AbstractModel):
    _name = 'nelsis.config'
    _description = 'Nelsis Field Force configuration helper'

    @api.model
    def param(self, key):
        val = self.env['ir.config_parameter'].sudo().get_param(key)
        return DEFAULTS.get(key, '') if val in (None, False) else val

    @api.model
    def int_param(self, key):
        try:
            return int(float(self.param(key)))
        except ValueError:
            return int(float(DEFAULTS[key]))

    @api.model
    def bool_param(self, key):
        return str(self.param(key)).lower() in ('1', 'true', 'yes')

    @api.model
    def app_config(self):
        """Settings that are safe to publish to the mobile app."""
        return {
            'track_interval_sec': self.int_param('nelsis.track_interval_sec'),
            'track_distance_m': self.int_param('nelsis.track_distance_m'),
            'max_accuracy_m': self.int_param('nelsis.max_accuracy_m'),
            'geofence_mode': self.param('nelsis.geofence_mode'),
            'require_photo_punch': self.bool_param('nelsis.require_photo_punch'),
            'block_mock': self.bool_param('nelsis.block_mock'),
            'stale_minutes': self.int_param('nelsis.stale_minutes'),
            'fcm': self._fcm_public(),
        }

    @api.model
    def _fcm_public(self):
        """Public Firebase client values (they are not secrets). The app starts Firebase from these, so no
        google-services.json has to be built into the APK. Empty dict = push not configured."""
        fcm = self.env['nelsis.fcm']
        vals = {'api_key': self.param('nelsis.fcm_api_key').strip(), 'app_id': self.param('nelsis.fcm_app_id').strip(),
                'sender_id': self.param('nelsis.fcm_sender_id').strip(), 'project_id': fcm.project_id()}
        return vals if fcm.configured() and all(vals.values()) else {}


class NelsisDashboardExtension(models.AbstractModel):
    """Hook: other Nelsis addons `_inherit` this model and extend `dashboard_extra`."""
    _name = 'nelsis.dashboard.extension'
    _description = 'Nelsis dashboard extension hook'

    @api.model
    def dashboard_extra(self, employees, date_from, date_to):
        return {}
