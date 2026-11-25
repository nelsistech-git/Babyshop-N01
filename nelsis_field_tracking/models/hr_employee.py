from datetime import timedelta

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    nl_tracking_enabled = fields.Boolean(string='GPS Tracking', default=True)
    nl_field_staff = fields.Boolean(
        string='Field Staff', help='Field staff are not restricted to work-site geofences when punching.')
    nl_site_ids = fields.Many2many('nelsis.work.site', string='Allowed Work Sites')
    nl_last_lat = fields.Float(digits=(10, 7), readonly=True)
    nl_last_lng = fields.Float(digits=(10, 7), readonly=True)
    nl_last_accuracy = fields.Float(readonly=True)
    nl_last_battery = fields.Integer(readonly=True)
    nl_last_device_time = fields.Datetime(readonly=True)
    nl_last_sync = fields.Datetime(string='Last Seen (server)', readonly=True)
    nl_last_app_version = fields.Char(readonly=True)
    nl_is_online = fields.Boolean(compute='_compute_nl_online', string='App Online')
    nl_log_count = fields.Integer(compute='_compute_nl_log_count')

    @api.depends('nl_last_sync')
    def _compute_nl_online(self):
        mins = self.env['nelsis.config'].int_param('nelsis.stale_minutes')
        limit = fields.Datetime.now() - timedelta(minutes=mins)
        for e in self:
            e.nl_is_online = bool(e.nl_last_sync and e.nl_last_sync >= limit)

    def _compute_nl_log_count(self):
        data = self.env['nelsis.location.log']._read_group(
            [('employee_id', 'in', self.ids)], ['employee_id'], ['__count'])
        counts = {emp.id: c for emp, c in data}
        for e in self:
            e.nl_log_count = counts.get(e.id, 0)

    def action_open_live_map(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client', 'tag': 'nelsis_live_map',
            'name': self.name, 'context': {'focus_employee_id': self.id},
        }

    def action_open_location_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'nelsis.location.log',
            'name': self.name, 'view_mode': 'tree,pivot,graph,form',
            'domain': [('employee_id', '=', self.id)],
        }
