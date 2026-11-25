from datetime import datetime, timedelta

import pytz

from odoo import api, fields, models

from .location_log import parse_dt


class NelsisPresenceLog(models.Model):
    _name = 'nelsis.presence.log'
    _description = 'App Online / Offline Events'
    _order = 'device_time desc, id desc'

    employee_id = fields.Many2one('hr.employee', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    state = fields.Selection([('online', 'Online'), ('offline', 'Offline')], required=True)
    kind = fields.Selection([
        ('app', 'Reported by app'), ('signal_lost', 'No signal (server detected)'),
        ('login', 'Login'), ('logout', 'Logout')], default='app', required=True)
    device_time = fields.Datetime(required=True, index=True)
    server_time = fields.Datetime(default=fields.Datetime.now, readonly=True)
    log_date = fields.Date(compute='_compute_log_date', store=True, index=True)
    client_uuid = fields.Char(copy=False, index=True)

    _sql_constraints = [('uuid_uniq', 'unique(client_uuid)', 'Duplicate event.')]

    @api.depends('device_time', 'employee_id.tz')
    def _compute_log_date(self):
        for r in self:
            tz = pytz.timezone(r.employee_id.tz or 'UTC')
            r.log_date = pytz.UTC.localize(r.device_time).astimezone(tz).date() if r.device_time else False

    @api.model
    def ingest(self, employee, events):
        accepted = []
        for ev in events or []:
            dt = parse_dt(ev.get('device_time'))
            uid = (ev.get('uuid') or '')[:64]
            if not dt or ev.get('state') not in ('online', 'offline'):
                continue
            if uid and self.sudo().search_count([('client_uuid', '=', uid)]):
                accepted.append(uid)
                continue
            self.sudo().create({'employee_id': employee.id, 'state': ev['state'], 'device_time': dt,
                                'client_uuid': uid or False})
            accepted.append(uid)
        return accepted

    @api.model
    def _cron_detect_signal_loss(self):
        """Employees who are punched in but silent for longer than the stale window get a
        server-side 'offline / signal lost' event (once), so admins can see the gap."""
        mins = self.env['nelsis.config'].int_param('nelsis.stale_minutes')
        limit = fields.Datetime.now() - timedelta(minutes=mins)
        open_att = self.env['hr.attendance'].sudo().search([('check_out', '=', False)])
        for emp in open_att.mapped('employee_id'):
            if not emp.nl_tracking_enabled or not emp.nl_last_sync or emp.nl_last_sync >= limit:
                continue
            last = self.sudo().search([('employee_id', '=', emp.id)], order='device_time desc', limit=1)
            if last and last.state == 'offline':
                continue
            self.sudo().create({'employee_id': emp.id, 'state': 'offline', 'kind': 'signal_lost',
                                'device_time': emp.nl_last_sync})
