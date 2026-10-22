# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, timedelta, time as dtime

import pytz

from odoo import models, fields, api, _

from ..utils.presence import analyze_presence, effective_minutes

_logger = logging.getLogger(__name__)

# Events created by the monitoring crons carry this marker so they are never
# mistaken for a real sighting of the employee (they have person_id set).
CRON_SOURCE = 'cctv_employee_monitor_cron'
PAD = timedelta(minutes=120)          # sightings are looked up this far outside the shift


class CctvEmployeeMonitor(models.Model):
    _name = 'cctv.employee.monitor'
    _description = 'Employee CCTV Monitoring Assignment'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    person_id = fields.Many2one('cctv.person', string='Linked Face Database Entry',
                                 domain="[('person_type', '=', 'employee')]",
                                 help='The cctv.person face-database record this employee is matched '
                                      'against by the face-recognition service. Required for any of '
                                      'the automatic checks below to run.')
    department_id = fields.Many2one('cctv.department', string='Assigned Zone/Workstation',
                                     help='Primary zone this employee is expected to be in during their shift')
    camera_ids = fields.Many2many('cctv.camera', string='Relevant Cameras',
                                   help='Cameras covering this employee\'s workstation/zone. If left '
                                        'blank, all cameras in the assigned zone are used.')
    shift_start = fields.Float(default=9.0, help='24h float in the EMPLOYEE\'S LOCAL TIME, e.g. 9.0 = 9:00 AM')
    shift_end = fields.Float(default=18.0,
                             help='If this is earlier than the start, the shift runs overnight into the next day.')
    grace_minutes = fields.Integer(default=15, help='Minutes of tolerance before flagging late arrival')
    idle_alert_minutes = fields.Integer(default=20,
                                         help='A gap: minutes with no detection before the employee is flagged '
                                              'as away from the workstation.')
    monitoring_active = fields.Boolean(default=True)
    notes = fields.Text()

    # ---- v4.3 gap-detection settings ------------------------------------------------------
    break_start = fields.Float(default=0.0, help='Scheduled break start (local time). Time inside the break '
                                                  'window is never counted as absence. Leave both at 0 for no break.')
    break_end = fields.Float(default=0.0)
    early_leave_tolerance = fields.Integer(
        string='Early-Leave Tolerance (min)', default=30,
        help='Flag an early departure only if the last detection is more than this many minutes before shift end.')
    alert_cooldown_minutes = fields.Integer(
        default=60, help='While an employee is still away, repeat the left-workstation alert at most this often. '
                         'One alert is always raised per gap.')
    gap_scope = fields.Selection([
        ('site', 'Seen anywhere on site'),
        ('zone', 'Seen by assigned zone / relevant cameras only'),
    ], default='site', string='Gap Counts When Not Seen...',
        help='"Anywhere on site" = detection by any camera counts as present. "Zone only" = the employee must be '
             'seen by the relevant cameras (or the assigned zone\'s cameras) to count as at their workstation.')
    skip_on_leave = fields.Boolean(default=True, string='Skip Approved Leave',
                                   help='Skip all checks on days the employee has validated time off '
                                        '(needs the Time Off app; ignored if it is not installed).')
    work_mon = fields.Boolean(string='Mon', default=True)
    work_tue = fields.Boolean(string='Tue', default=True)
    work_wed = fields.Boolean(string='Wed', default=True)
    work_thu = fields.Boolean(string='Thu', default=True)
    work_fri = fields.Boolean(string='Fri', default=True)
    work_sat = fields.Boolean(string='Sat', default=True)
    work_sun = fields.Boolean(string='Sun', default=True)
    effective_tz = fields.Char(compute='_compute_effective_tz', string='Time Zone Used')

    _sql_constraints = [
        ('employee_uniq', 'unique(employee_id)', 'Each employee can only have one monitoring assignment.'),
    ]

    # ------------------------------------------------------------------------------------------
    # Time-zone & shift-window helpers
    # ------------------------------------------------------------------------------------------
    def _tz_name(self):
        self.ensure_one()
        return self.employee_id.tz or self.env.user.tz or 'UTC'

    @api.depends('employee_id.tz')
    def _compute_effective_tz(self):
        for rec in self:
            rec.effective_tz = rec._tz_name()

    def _get_tz(self):
        self.ensure_one()
        try:
            return pytz.timezone(self._tz_name())
        except pytz.UnknownTimeZoneError:
            return pytz.utc

    def _local_to_utc(self, local_date, hour_float):
        """Local date + 24h float (can exceed 24) -> naive UTC datetime."""
        naive = datetime.combine(local_date, dtime.min) + timedelta(minutes=round(hour_float * 60))
        return self._get_tz().localize(naive).astimezone(pytz.utc).replace(tzinfo=None)

    def _shift_window(self, local_date):
        self.ensure_one()
        end_hour = self.shift_end if self.shift_end > self.shift_start else self.shift_end + 24.0
        return self._local_to_utc(local_date, self.shift_start), self._local_to_utc(local_date, end_hour)

    def _break_window(self, local_date, shift_start_utc):
        """Break window (naive UTC) for the shift that starts on local_date, or None."""
        self.ensure_one()
        if self.break_end <= self.break_start:
            return None
        bs = self._local_to_utc(local_date, self.break_start)
        be = self._local_to_utc(local_date, self.break_end)
        if bs < shift_start_utc:      # overnight shift: break falls after midnight
            bs += timedelta(days=1)
            be += timedelta(days=1)
        return bs, be

    def _active_shift(self, now):
        """(local_date, start_utc, end_utc) of the shift that `now` belongs to
        (including the 2h padding either side), else None."""
        self.ensure_one()
        local_today = pytz.utc.localize(now).astimezone(self._get_tz()).date()
        for d in (local_today, local_today - timedelta(days=1)):
            s, e = self._shift_window(d)
            if s - PAD <= now <= e + PAD:
                return d, s, e
        return None

    def _shifts_to_summarize(self, now):
        """Shifts that have started and ended less than 6h ago (or are in progress)."""
        self.ensure_one()
        local_today = pytz.utc.localize(now).astimezone(self._get_tz()).date()
        out = []
        for d in (local_today - timedelta(days=1), local_today):
            s, e = self._shift_window(d)
            if s <= now <= e + timedelta(hours=6):
                out.append((d, s, e))
        return out

    def _is_expected_to_work(self, local_date, start, end):
        """Working weekday, no public holiday, no approved leave."""
        self.ensure_one()
        flags = (self.work_mon, self.work_tue, self.work_wed, self.work_thu,
                 self.work_fri, self.work_sat, self.work_sun)
        if not flags[local_date.weekday()]:
            return False
        cal = self.employee_id.resource_calendar_id
        dom = [('resource_id', '=', False), ('date_from', '<', end), ('date_to', '>', start)]
        if cal:
            dom += ['|', ('calendar_id', '=', False), ('calendar_id', '=', cal.id)]
        else:
            dom += [('calendar_id', '=', False)]
        if self.env['resource.calendar.leaves'].sudo().search_count(dom):
            return False
        if self.skip_on_leave and 'hr.leave' in self.env:
            if self.env['hr.leave'].sudo().search_count([
                    ('employee_id', '=', self.employee_id.id), ('state', '=', 'validate'),
                    ('date_from', '<', end), ('date_to', '>', start)]):
                return False
        return True

    # ------------------------------------------------------------------------------------------
    # Sightings
    # ------------------------------------------------------------------------------------------
    def _scope_camera_ids(self):
        self.ensure_one()
        if self.gap_scope != 'zone':
            return []
        return (self.camera_ids or self.department_id.camera_ids).ids

    def _sightings(self, date_from, date_to):
        """Sorted datetimes the employee was genuinely detected (own cron alerts excluded)."""
        self.ensure_one()
        if not self.person_id:
            return []
        cams = self._scope_camera_ids()
        ev_dom = [('person_id', '=', self.person_id.id),
                  ('event_time', '>=', date_from), ('event_time', '<=', date_to),
                  ('source_service', '!=', CRON_SOURCE)]
        fl_dom = [('person_id', '=', self.person_id.id),
                  ('detected_at', '>=', date_from), ('detected_at', '<=', date_to)]
        if cams:
            ev_dom.append(('camera_id', 'in', cams))
            fl_dom.append(('camera_id', 'in', cams))
        times = [r['event_time'] for r in self.env['cctv.event'].search_read(ev_dom, ['event_time'])]
        times += [r['detected_at'] for r in self.env['cctv.face.log'].search_read(fl_dom, ['detected_at'])]
        return sorted(t for t in times if t)

    def _last_seen_datetime(self):
        """Most recent genuine detection in the current shift (kept for other modules)."""
        self.ensure_one()
        shift = self._active_shift(fields.Datetime.now())
        if not shift:
            return None
        s = self._sightings(shift[1] - PAD, fields.Datetime.now())
        return s[-1] if s else None

    def _first_seen_datetime(self):
        self.ensure_one()
        shift = self._active_shift(fields.Datetime.now())
        if not shift:
            return None
        s = self._sightings(shift[1] - PAD, fields.Datetime.now())
        return s[0] if s else None

    def _analyze_shift(self, local_date, start, end, now):
        self.ensure_one()
        brk = self._break_window(local_date, start)
        cap = min(now, end + PAD)
        pts = self._sightings(start - PAD, cap)
        res = analyze_presence(pts, start, end, now, self.idle_alert_minutes, brk)
        res['break'] = brk
        res['break_minutes'] = (effective_minutes(start, end) - effective_minutes(start, end, brk)) if brk else 0.0
        res['scheduled_minutes'] = effective_minutes(start, end, brk)
        return res

    # ------------------------------------------------------------------------------------------
    # Alerts (deduplicated)
    # ------------------------------------------------------------------------------------------
    def _already_alerted(self, behavior_type, since):
        self.ensure_one()
        return self.env['cctv.event'].search_count([
            ('person_id', '=', self.person_id.id), ('behavior_type', '=', behavior_type),
            ('source_service', '=', CRON_SOURCE), ('event_time', '>=', since)])

    def _create_compliance_alert(self, behavior_type, message, extra=None, severity=None):
        """Create the cctv.event. Severity/alert/incident are derived from behavior_type by
        cctv.event.create (``severity`` is accepted only for backward compatibility)."""
        self.ensure_one()
        camera = (self.camera_ids[:1] or self.department_id.camera_ids[:1]
                  or self.env['cctv.camera'].search([], limit=1))
        if not camera:
            _logger.warning('Employee monitor %s: no camera available to attach %s alert to.',
                            self.employee_id.name, behavior_type)
            return False
        payload = {'message': message, 'employee': self.employee_id.name}
        payload.update(extra or {})
        return self.env['cctv.event'].create({
            'camera_id': camera.id,
            'detection_type': 'human',
            'behavior_type': behavior_type,
            'person_id': self.person_id.id,
            'confidence': 100.0,
            'source_service': CRON_SOURCE,
            'raw_payload': json.dumps(payload, default=str),
        })

    # ------------------------------------------------------------------------------------------
    # Crons
    # ------------------------------------------------------------------------------------------
    @api.model
    def _run_checks(self, method_name):
        now = fields.Datetime.now()
        for mon in self.search([('monitoring_active', '=', True), ('person_id', '!=', False)]):
            try:
                with self.env.cr.savepoint():
                    getattr(mon, method_name)(now)
            except Exception:
                _logger.exception('Employee monitor %s failed for %s', method_name, mon.employee_id.name)

    @api.model
    def cron_check_late_arrivals(self):
        self._run_checks('_check_late_arrival')

    @api.model
    def cron_check_early_departures(self):
        self._run_checks('_check_early_departure')

    @api.model
    def cron_check_left_station(self):
        self._run_checks('_check_left_station')

    def _check_late_arrival(self, now):
        self.ensure_one()
        shift = self._active_shift(now)
        if not shift:
            return
        d, s, e = shift
        deadline = s + timedelta(minutes=self.grace_minutes)
        if now < deadline or now > e or not self._is_expected_to_work(d, s, e):
            return
        sightings = self._sightings(s - PAD, now)
        if self._already_alerted('late_arrival', s - PAD):
            return
        if not sightings:
            self._create_compliance_alert(
                'late_arrival', _('%s not detected by shift start + grace period.', self.employee_id.name),
                {'minutes_late': None})
        elif sightings[0] > deadline:
            late = int((sightings[0] - s).total_seconds() / 60.0)
            self._create_compliance_alert(
                'late_arrival', _('%(emp)s first detected %(m)s min after shift start.',
                                  emp=self.employee_id.name, m=late), {'minutes_late': late})

    def _check_early_departure(self, now):
        self.ensure_one()
        shift = self._active_shift(now)
        if not shift:
            return
        d, s, e = shift
        if now < e or not self._is_expected_to_work(d, s, e):
            return
        sightings = self._sightings(s - PAD, now)
        if not sightings:
            return          # never seen at all -> reported as a late arrival / absence instead
        last = sightings[-1]
        early = (e - last).total_seconds() / 60.0
        if (early > self.early_leave_tolerance
                and (now - last).total_seconds() / 60.0 >= self.idle_alert_minutes
                and not self._already_alerted('early_departure', s - PAD)):
            self._create_compliance_alert(
                'early_departure',
                _('Possible early departure: %(emp)s last detected %(m)s min before shift end.',
                  emp=self.employee_id.name, m=int(early)),
                {'minutes_early': int(early), 'last_seen': last})

    def _check_left_station(self, now):
        """During the shift (outside the break) flag an open gap >= idle_alert_minutes:
        one alert per gap, repeated at most every alert_cooldown_minutes while still away."""
        self.ensure_one()
        shift = self._active_shift(now)
        if not shift:
            return
        d, s, e = shift
        if not (s <= now <= e) or not self._is_expected_to_work(d, s, e):
            return
        brk = self._break_window(d, s)
        if brk and brk[0] <= now <= brk[1]:
            return
        sightings = self._sightings(s - PAD, now)
        if not sightings:
            return          # not seen yet today -> handled by the late-arrival check
        last = sightings[-1]
        gone = effective_minutes(max(last, s), now, brk)
        if gone < self.idle_alert_minutes:
            return
        prev = self.env['cctv.event'].search([
            ('person_id', '=', self.person_id.id), ('behavior_type', '=', 'left_station'),
            ('source_service', '=', CRON_SOURCE), ('event_time', '>=', s - PAD)],
            order='event_time desc', limit=1)
        if prev and prev.event_time > last and \
                (now - prev.event_time) < timedelta(minutes=self.alert_cooldown_minutes):
            return
        self._create_compliance_alert(
            'left_station',
            _('%(emp)s not detected at assigned zone for %(m)s min during shift hours.',
              emp=self.employee_id.name, m=int(gone)),
            {'minutes_away': int(gone), 'last_seen': last})

    # ------------------------------------------------------------------------------------------
    # UI helper
    # ------------------------------------------------------------------------------------------
    def action_rebuild_summary(self):
        """Rebuild the daily summary row(s) for the current/most recent shift now."""
        now = fields.Datetime.now()
        Summary = self.env['cctv.employee.daily.summary'].sudo()
        built = Summary
        for mon in self:
            for d, s, e in mon._shifts_to_summarize(now):
                built |= Summary._build_for_monitor(mon, d, s, e, now)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Employee summary'), 'type': 'success', 'sticky': False,
                       'message': _('%s summary row(s) updated.', len(built))},
        }


class CctvEmployeeDailySummary(models.Model):
    _name = 'cctv.employee.daily.summary'
    _description = 'Employee Daily Activity Summary (from CCTV events)'
    _order = 'date desc'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', required=True, index=True)
    date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    first_seen = fields.Datetime()
    last_seen = fields.Datetime()
    idle_event_count = fields.Integer()
    phone_usage_count = fields.Integer()
    unauthorized_break_count = fields.Integer()
    left_station_count = fields.Integer()
    late_arrival = fields.Boolean()
    early_departure = fields.Boolean()
    unprofessional_conduct_count = fields.Integer()
    total_violation_count = fields.Integer(compute='_compute_total_violations', store=True)

    # ---- v4.3 presence / gap analytics (break time is never counted as absence) ----
    scheduled_minutes = fields.Integer(string='Scheduled (min)', help='Shift length minus scheduled break')
    late_minutes = fields.Integer(string='Minutes Late', help='Minutes between shift start and first detection')
    early_departure_minutes = fields.Integer(string='Minutes Left Early')
    gap_count = fields.Integer(string='Gaps', help='Periods with no detection of at least the "idle alert" threshold')
    total_gap_minutes = fields.Integer(string='Total Gap (min)')
    longest_gap_minutes = fields.Integer(string='Longest Gap (min)')
    presence_minutes = fields.Integer(string='Present (min)')
    presence_rate = fields.Float(string='Presence %', digits=(5, 1))
    gap_detail = fields.Text(string='Gap Detail', help='Local-time list of each detected gap')

    _sql_constraints = [
        ('employee_date_uniq', 'unique(employee_id, date)', 'Only one summary per employee per day.'),
    ]

    @api.depends('idle_event_count', 'phone_usage_count', 'unauthorized_break_count',
                 'left_station_count', 'unprofessional_conduct_count', 'late_arrival', 'early_departure')
    def _compute_total_violations(self):
        for rec in self:
            rec.total_violation_count = (
                rec.idle_event_count + rec.phone_usage_count + rec.unauthorized_break_count
                + rec.left_station_count + rec.unprofessional_conduct_count
                + (1 if rec.late_arrival else 0) + (1 if rec.early_departure else 0)
            )

    @api.model
    def _build_for_monitor(self, mon, local_date, start, end, now):
        """Create/update the summary row of one employee for one shift. Returns the record
        (empty recordset if the employee was never seen and nothing was raised)."""
        mon.ensure_one()
        cap = min(now, end + PAD)
        events = self.env['cctv.event'].search([
            ('person_id', '=', mon.person_id.id),
            ('event_time', '>=', start - PAD), ('event_time', '<=', cap)])
        a = mon._analyze_shift(local_date, start, end, now)
        if not events and not a['first_seen']:
            return self.browse()

        tz = mon._get_tz()

        def hhmm(dt):
            return pytz.utc.localize(dt).astimezone(tz).strftime('%H:%M')

        def count(*types):
            return len(events.filtered(lambda ev: ev.behavior_type in types))

        late_flag = bool(count('late_arrival')) or a['late_minutes'] > mon.grace_minutes
        early_flag = bool(count('early_departure')) or a['early_minutes'] > mon.early_leave_tolerance
        vals = {
            'employee_id': mon.employee_id.id,
            'date': local_date,
            'first_seen': a['first_seen'],
            'last_seen': a['last_seen'],
            'idle_event_count': count('idle'),
            'phone_usage_count': count('phone_usage'),
            'unauthorized_break_count': count('unauthorized_break'),
            'left_station_count': count('left_station'),
            'late_arrival': late_flag,
            'early_departure': early_flag,
            'unprofessional_conduct_count': count('unprofessional_conduct', 'argument',
                                                  'group_gathering', 'personal_visitor'),
            'scheduled_minutes': int(round(a['scheduled_minutes'])),
            'late_minutes': int(round(a['late_minutes'])),
            'early_departure_minutes': int(round(a['early_minutes'])),
            'gap_count': a['gap_count'],
            'total_gap_minutes': int(round(a['total_gap_minutes'])),
            'longest_gap_minutes': int(round(a['longest_gap_minutes'])),
            'presence_minutes': int(round(a['presence_minutes'])),
            'presence_rate': round(a['presence_rate'], 1),
            'gap_detail': '\n'.join(
                f"{hhmm(g[0])} - {hhmm(g[1])}  ({int(round(g[2]))} min)" for g in a['gaps']) or False,
        }
        existing = self.search([('employee_id', '=', mon.employee_id.id), ('date', '=', local_date)], limit=1)
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)

    @api.model
    def cron_build_daily_summaries(self):
        """Hourly: (re)build the summary of every shift in progress or ended < 6h ago, so the
        final numbers of a day are always written after the shift has closed."""
        now = fields.Datetime.now()
        monitors = self.env['cctv.employee.monitor'].search([('person_id', '!=', False)])
        for mon in monitors:
            try:
                with self.env.cr.savepoint():
                    for d, s, e in mon._shifts_to_summarize(now):
                        self._build_for_monitor(mon, d, s, e, now)
            except Exception:
                _logger.exception('Daily summary failed for %s', mon.employee_id.name)
