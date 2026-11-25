import logging
from datetime import datetime, timedelta

import pytz

from odoo import api, fields, models

from ..utils.geo import haversine_m, valid_coords

_logger = logging.getLogger(__name__)

MAX_SPEED_KMH = 160.0       # anything faster between two fixes is treated as a GPS jump
MAX_GAP_MIN = 30            # no distance accumulated across longer gaps (signal lost)


def parse_dt(value):
    """ISO-8601 (with Z/offset) -> naive UTC datetime, or None."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    if dt.tzinfo:
        dt = dt.astimezone(pytz.UTC).replace(tzinfo=None)
    return dt


class NelsisLocationLog(models.Model):
    _name = 'nelsis.location.log'
    _description = 'Employee Location Log'
    _order = 'device_time desc, id desc'

    employee_id = fields.Many2one('hr.employee', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='employee_id.company_id', store=True, index=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    latitude = fields.Float(digits=(10, 7), required=True)
    longitude = fields.Float(digits=(10, 7), required=True)
    accuracy = fields.Float(string='Accuracy (m)')
    speed_kmh = fields.Float(string='Speed (km/h)')
    heading = fields.Float()
    battery = fields.Integer(string='Battery %')
    source = fields.Selection([
        ('auto', 'Auto Tracking'), ('punch_in', 'Punch In'), ('punch_out', 'Punch Out'),
        ('expense', 'Expense / Bill'), ('manual', 'Manual'),
    ], default='auto', required=True, index=True)
    device_time = fields.Datetime(required=True, index=True, help='Time the fix was captured on the phone (UTC).')
    server_time = fields.Datetime(default=fields.Datetime.now, readonly=True,
                                  help='Time the server received the fix.')
    log_date = fields.Date(compute='_compute_log_date', store=True, index=True)
    delay_min = fields.Float(string='Sync Delay (min)', compute='_compute_flags', store=True)
    is_offline_sync = fields.Boolean(string='Synced Late (offline)', compute='_compute_flags', store=True)
    time_trust = fields.Selection([
        ('ok', 'On time'), ('delayed', 'Delayed (offline)'), ('drift', 'Clock mismatch')],
        compute='_compute_flags', store=True, string='Time Check')
    is_mock = fields.Boolean(string='Mock GPS')
    is_teleport = fields.Boolean(string='GPS Jump', readonly=True)
    low_accuracy = fields.Boolean(compute='_compute_flags', store=True)
    is_genuine = fields.Boolean(string='Genuine', compute='_compute_flags', store=True,
                                help='True when not mock GPS, no clock mismatch and no impossible jump.')
    distance_m = fields.Float(string='Distance from previous (m)', readonly=True)
    address = fields.Char()
    attendance_id = fields.Many2one('hr.attendance', ondelete='set null', index=True)
    client_uuid = fields.Char(index=True, copy=False)

    _sql_constraints = [
        ('uuid_uniq', 'unique(client_uuid)', 'Duplicate location point.'),
    ]

    # ------------------------------------------------------------------ computes
    @api.depends('device_time', 'employee_id.tz')
    def _compute_log_date(self):
        for r in self:
            tz = pytz.timezone(r.employee_id.tz or self.env.user.tz or 'UTC')
            r.log_date = pytz.UTC.localize(r.device_time).astimezone(tz).date() if r.device_time else False

    @api.depends('device_time', 'server_time', 'accuracy', 'is_mock', 'is_teleport')
    def _compute_flags(self):
        tol = self.env['nelsis.config'].int_param('nelsis.time_tolerance_sec')
        max_acc = self.env['nelsis.config'].int_param('nelsis.max_accuracy_m')
        for r in self:
            if r.device_time and r.server_time:
                delta = (r.server_time - r.device_time).total_seconds()
            else:
                delta = 0
            r.delay_min = round(max(delta, 0) / 60.0, 1)
            if delta < -tol:
                r.time_trust = 'drift'
            elif delta > 180:
                r.time_trust = 'delayed'
            else:
                r.time_trust = 'ok'
            r.is_offline_sync = r.time_trust == 'delayed'
            r.low_accuracy = bool(r.accuracy and r.accuracy > max_acc)
            r.is_genuine = not r.is_mock and not r.is_teleport and r.time_trust != 'drift'

    # ------------------------------------------------------------------ ingest API
    @api.model
    def ingest(self, employee, points, default_source='auto', attendance=None):
        """Store a batch of GPS fixes captured by the app (online or buffered offline).
        Idempotent on `client_uuid`. Returns {'accepted': [...], 'duplicates': [...], 'rejected': [...]}."""
        res = {'accepted': [], 'duplicates': [], 'rejected': []}
        clean = []
        for p in points or []:
            uid = (p.get('uuid') or '')[:64]
            dt = parse_dt(p.get('device_time'))
            if not valid_coords(p.get('lat'), p.get('lng')) or not dt:
                res['rejected'].append({'uuid': uid, 'reason': 'invalid_data'})
                continue
            clean.append((dt, uid, p))
        clean.sort(key=lambda x: x[0])
        existing = set()
        uuids = [u for _, u, _ in clean if u]
        if uuids:
            existing = set(self.sudo().search([('client_uuid', 'in', uuids)]).mapped('client_uuid'))
        now = fields.Datetime.now()
        newest = None
        for dt, uid, p in clean:
            if uid and uid in existing:
                res['duplicates'].append(uid)
                continue
            lat, lng = float(p['lat']), float(p['lng'])
            prev = self.sudo().search([('employee_id', '=', employee.id), ('device_time', '<', dt)],
                                      order='device_time desc', limit=1)
            dist, teleport = 0.0, False
            if prev:
                gap_min = (dt - prev.device_time).total_seconds() / 60.0
                if 0 < gap_min <= MAX_GAP_MIN:
                    dist = haversine_m(prev.latitude, prev.longitude, lat, lng)
                    if dist < 8:
                        dist = 0.0
                    if dist / 1000.0 / (gap_min / 60.0) > MAX_SPEED_KMH and dist > 500:
                        teleport = True
            source = p.get('source') if p.get('source') in dict(self._fields['source'].selection) else default_source
            rec = self.sudo().create({
                'employee_id': employee.id, 'latitude': lat, 'longitude': lng,
                'accuracy': p.get('accuracy') or 0, 'speed_kmh': (p.get('speed') or 0) * 3.6,
                'heading': p.get('heading') or 0, 'battery': int(p.get('battery') or 0),
                'source': source, 'device_time': dt, 'server_time': now,
                'is_mock': bool(p.get('mock')), 'is_teleport': teleport,
                'distance_m': dist, 'client_uuid': uid or False,
                'address': (p.get('address') or '')[:250] or False,
                'attendance_id': attendance.id if attendance else False,
            })
            res['accepted'].append(uid or rec.id)
            if newest is None or dt > newest[0]:
                newest = (dt, rec)
        if newest:
            dt, rec = newest
            if not employee.nl_last_device_time or dt >= employee.nl_last_device_time:
                employee.sudo().write({
                    'nl_last_lat': rec.latitude, 'nl_last_lng': rec.longitude,
                    'nl_last_accuracy': rec.accuracy, 'nl_last_battery': rec.battery,
                    'nl_last_device_time': dt,
                })
        employee.sudo().write({'nl_last_sync': now})
        return res

    # ------------------------------------------------------------------ map feeds
    @api.model
    def _map_domain_employees(self, filters):
        dom = [('nl_tracking_enabled', '=', True)]
        if filters.get('department_id'):
            dom.append(('department_id', '=', int(filters['department_id'])))
        if filters.get('employee_id'):
            dom.append(('id', '=', int(filters['employee_id'])))
        if filters.get('search'):
            dom.append(('name', 'ilike', filters['search']))
        return dom

    @api.model
    def get_live_map_data(self, filters=None):
        """Feed of the Live Map. Everything the OWL client needs in one RPC."""
        filters = filters or {}
        self.env['hr.employee'].check_access_rights('read')
        if not self.env.user.has_group('nelsis_field_tracking.group_nelsis_manager'):
            return {'employees': [], 'summary': {}, 'error': 'forbidden'}
        Emp = self.env['hr.employee']
        emps = Emp.search(self._map_domain_employees(filters))
        today = fields.Date.context_today(self)
        day = fields.Date.to_date(filters.get('date')) or today
        att = self.env['hr.attendance'].search([
            ('employee_id', 'in', emps.ids), ('check_in', '>=', datetime.combine(day, datetime.min.time()) - timedelta(hours=14)),
            ('check_in', '<', datetime.combine(day + timedelta(days=1), datetime.min.time()) + timedelta(hours=10)),
        ])
        att_by_emp = {}
        for a in att.sorted('check_in'):
            # the search window is padded for time zones; keep only attendances that start on the chosen local day
            if fields.Datetime.context_timestamp(a, a.check_in).date() != day:
                continue
            att_by_emp.setdefault(a.employee_id.id, []).append(a)
        dist = {emp.id: d for emp, d in self._read_group(
            [('employee_id', 'in', emps.ids), ('log_date', '=', day)], ['employee_id'], ['distance_m:sum'])}
        flagged = {emp.id: c for emp, c in self._read_group(
            [('employee_id', 'in', emps.ids), ('log_date', '=', day), ('is_genuine', '=', False)],
            ['employee_id'], ['__count'])}
        out = []
        summary = {'total': 0, 'online': 0, 'offline': 0, 'punched_in': 0, 'flagged': 0, 'no_location': 0}
        for e in emps:
            a_list = att_by_emp.get(e.id, [])
            open_att = next((a for a in a_list if not a.check_out), None)
            status = 'punched_in' if open_att else ('punched_out' if a_list else 'no_attendance')
            has_pos = bool(e.nl_last_device_time)
            item = {
                'id': e.id, 'name': e.name, 'job': e.job_title or '',
                'department': e.department_id.name or '', 'department_id': e.department_id.id,
                'lat': e.nl_last_lat if has_pos else None, 'lng': e.nl_last_lng if has_pos else None,
                'accuracy': e.nl_last_accuracy, 'battery': e.nl_last_battery,
                'last_seen': fields.Datetime.to_string(e.nl_last_sync) if e.nl_last_sync else '',
                'last_fix': fields.Datetime.to_string(e.nl_last_device_time) if e.nl_last_device_time else '',
                'online': e.nl_is_online, 'attendance': status,
                'check_in': fields.Datetime.to_string(a_list[0].check_in) if a_list else '',
                'check_out': fields.Datetime.to_string(a_list[-1].check_out) if a_list and a_list[-1].check_out else '',
                'distance_km': round((dist.get(e.id) or 0) / 1000.0, 2),
                'flags': flagged.get(e.id, 0),
                'app_version': e.nl_last_app_version or '',
            }
            out.append(item)
            summary['total'] += 1
            summary['online'] += 1 if e.nl_is_online else 0
            summary['offline'] += 0 if e.nl_is_online else 1
            summary['punched_in'] += 1 if open_att else 0
            summary['flagged'] += 1 if item['flags'] else 0
            summary['no_location'] += 0 if has_pos else 1
        sites = self.env['nelsis.work.site'].search([])
        return {
            'employees': out, 'summary': summary, 'date': fields.Date.to_string(day),
            'sites': [{'id': s.id, 'name': s.name, 'lat': s.latitude, 'lng': s.longitude, 'radius': s.radius_m}
                      for s in sites],
            'departments': [{'id': d.id, 'name': d.name} for d in self.env['hr.department'].search([])],
            'google_key': self.env['nelsis.config'].param('nelsis.google_maps_key'),
            'server_time': fields.Datetime.to_string(fields.Datetime.now()),
        }

    @api.model
    def get_route_data(self, employee_id, date):
        """Track points + punch markers for one employee on one day, with true/false checks."""
        if not self.env.user.has_group('nelsis_field_tracking.group_nelsis_manager'):
            return {'points': [], 'punches': []}
        day = fields.Date.to_date(date)
        logs = self.search([('employee_id', '=', int(employee_id)), ('log_date', '=', day)],
                           order='device_time asc', limit=2000)
        points = [{
            'id': l.id, 'lat': l.latitude, 'lng': l.longitude, 'acc': l.accuracy,
            'time': fields.Datetime.to_string(l.device_time), 'server_time': fields.Datetime.to_string(l.server_time),
            'source': l.source, 'genuine': l.is_genuine, 'mock': l.is_mock, 'trust': l.time_trust,
            'delay_min': l.delay_min, 'battery': l.battery, 'jump': l.is_teleport,
        } for l in logs]
        atts = self.env['hr.attendance'].search([('employee_id', '=', int(employee_id))], order='check_in asc')
        punches = []
        for a in atts:
            ci_day = fields.Datetime.context_timestamp(self, a.check_in).date()
            if ci_day != day:
                continue
            if a.in_latitude or a.in_longitude:
                punches.append({'type': 'in', 'lat': a.in_latitude, 'lng': a.in_longitude,
                                'time': fields.Datetime.to_string(a.check_in), 'status': a.nl_geo_status,
                                'genuine': a.nl_in_genuine, 'offline': a.nl_in_offline,
                                'distance_m': a.nl_in_distance_m, 'site': a.nl_in_site_id.name or ''})
            if a.check_out and (a.out_latitude or a.out_longitude):
                punches.append({'type': 'out', 'lat': a.out_latitude, 'lng': a.out_longitude,
                                'time': fields.Datetime.to_string(a.check_out), 'status': a.nl_geo_status,
                                'genuine': a.nl_out_genuine, 'offline': a.nl_out_offline,
                                'distance_m': a.nl_out_distance_m, 'site': a.nl_out_site_id.name or ''})
        presence = self.env['nelsis.presence.log'].search(
            [('employee_id', '=', int(employee_id)), ('log_date', '=', day)], order='device_time asc')
        return {
            'points': points, 'punches': punches,
            'distance_km': round(sum(l.distance_m for l in logs) / 1000.0, 2),
            'presence': [{'state': p.state, 'time': fields.Datetime.to_string(p.device_time),
                          'kind': p.kind} for p in presence],
        }

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None, department_id=None):
        if not self.env.user.has_group('nelsis_field_tracking.group_nelsis_manager'):
            return {}
        today = fields.Date.context_today(self)
        d_to = fields.Date.to_date(date_to) or today
        d_from = fields.Date.to_date(date_from) or (d_to - timedelta(days=13))
        edom = [('nl_tracking_enabled', '=', True)]
        if department_id:
            edom.append(('department_id', '=', int(department_id)))
        emps = self.env['hr.employee'].search(edom)
        ldom = [('employee_id', 'in', emps.ids), ('log_date', '>=', d_from), ('log_date', '<=', d_to)]
        Att = self.env['hr.attendance']
        adom = [('employee_id', 'in', emps.ids), ('check_in', '>=', datetime.combine(d_from, datetime.min.time())),
                ('check_in', '<', datetime.combine(d_to + timedelta(days=1), datetime.min.time()))]
        atts = Att.search(adom)
        by_day, hours_by_emp = {}, {}
        for a in atts:
            d = fields.Datetime.context_timestamp(self, a.check_in).date()
            by_day.setdefault(d, set()).add(a.employee_id.id)
            hours_by_emp[a.employee_id.name] = hours_by_emp.get(a.employee_id.name, 0) + (a.worked_hours or 0)
        days = [d_from + timedelta(days=i) for i in range((d_to - d_from).days + 1)]
        dist = self._read_group(ldom, ['employee_id'], ['distance_m:sum'], order='distance_m:sum desc', limit=10)
        total_m = (self._read_group(ldom, [], ['distance_m:sum']) or [(0,)])[0][0] or 0
        flags = {
            'Mock GPS': self.search_count(ldom + [('is_mock', '=', True)]),
            'Clock mismatch': self.search_count(ldom + [('time_trust', '=', 'drift')]),
            'GPS jump': self.search_count(ldom + [('is_teleport', '=', True)]),
            'Low accuracy': self.search_count(ldom + [('low_accuracy', '=', True)]),
            'Offline sync': self.search_count(ldom + [('is_offline_sync', '=', True)]),
        }
        outside = Att.search_count(adom + [('nl_geo_status', '=', 'outside')])
        open_now = Att.search_count([('employee_id', 'in', emps.ids), ('check_out', '=', False)])
        online_now = len(emps.filtered('nl_is_online'))
        present_today = len(by_day.get(today, []))
        data = {
            'kpis': {
                'employees': len(emps), 'present_today': present_today, 'punched_in_now': open_now,
                'online_now': online_now, 'offline_now': len(emps) - online_now,
                'absent_today': max(len(emps) - present_today, 0),
                'flags': sum(v for k, v in flags.items() if k in ('Mock GPS', 'Clock mismatch', 'GPS jump')),
                'outside_geofence': outside,
                'distance_km': round(total_m / 1000.0, 1),
            },
            'attendance_trend': {'labels': [d.strftime('%d %b') for d in days],
                                 'values': [len(by_day.get(d, [])) for d in days]},
            'top_hours': sorted(((k, round(v, 1)) for k, v in hours_by_emp.items()), key=lambda x: -x[1])[:8],
            'top_distance': [(e.name, round((d or 0) / 1000.0, 1)) for e, d in dist],
            'flags': flags,
            'date_from': fields.Date.to_string(d_from), 'date_to': fields.Date.to_string(d_to),
            'departments': [{'id': d.id, 'name': d.name} for d in self.env['hr.department'].search([])],
        }
        # other Nelsis modules (expense, AI) extend the dashboard
        data.update(self.env['nelsis.dashboard.extension'].dashboard_extra(emps, d_from, d_to))
        return data

    @api.model
    def _cron_purge(self):
        days = self.env['nelsis.config'].int_param('nelsis.retention_days')
        limit = fields.Datetime.now() - timedelta(days=days)
        self.sudo().search([('device_time', '<', limit), ('source', '=', 'auto')]).unlink()
        self.env['nelsis.presence.log'].sudo().search([('device_time', '<', limit)]).unlink()
