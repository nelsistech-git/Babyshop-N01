import statistics
from datetime import datetime, timedelta

from odoo import api, fields, models, _

from odoo.addons.nelsis_field_tracking.utils.geo import haversine_m


LATE_HOUR = 10      # local hour after which a check-in counts as late


class NelsisAiEngine(models.AbstractModel):
    """Rule + statistics based detectors. They run without any external service, so the module
    works offline; the optional LLM only writes explanations."""
    _name = 'nelsis.ai.engine'
    _description = 'Nelsis AI risk engine'

    # ---------------------------------------------------------------- helpers
    def _add(self, fp, kind, severity, score, emp, name, desc, date=None, res=None):
        Insight = self.env['nelsis.ai.insight'].sudo()
        if Insight.with_context(active_test=False).search_count([('fingerprint', '=', fp)]):
            return False
        vals = {'fingerprint': fp, 'kind': kind, 'severity': severity, 'score': score, 'employee_id': emp.id,
                'name': name, 'description': desc, 'date': date or fields.Date.today()}
        if res:
            vals.update(res_model=res._name, res_id=res.id)
        return Insight.create(vals)

    # ---------------------------------------------------------------- scan
    @api.model
    def scan(self, days=3):
        since = fields.Date.today() - timedelta(days=days)
        self._scan_logs(since)
        self._scan_attendance(since)
        self._scan_expenses(since)
        self._scan_patterns()
        return True

    def _scan_logs(self, since):
        Log = self.env['nelsis.location.log'].sudo()
        groups = Log._read_group(
            [('log_date', '>=', since), ('is_genuine', '=', False)], ['employee_id', 'log_date:day'], ['__count'])
        for emp, day, n in groups:
            logs = Log.search([('employee_id', '=', emp.id), ('log_date', '=', day), ('is_genuine', '=', False)])
            mock = len(logs.filtered('is_mock'))
            drift = len(logs.filtered(lambda l: l.time_trust == 'drift'))
            jump = len(logs.filtered('is_teleport'))
            if mock:
                self._add('mock-%s-%s' % (emp.id, day), 'fake_gps', '3', 90, emp,
                          _('%(e)s used mock GPS on %(d)s', e=emp.name, d=day),
                          _('%s location points were flagged as mock/fake GPS.') % mock, day)
            if drift:
                self._add('clock-%s-%s' % (emp.id, day), 'clock', '2', 70, emp,
                          _('%(e)s phone clock mismatch on %(d)s', e=emp.name, d=day),
                          _('%s points had a phone time that disagrees with the server (possible clock tampering).') % drift, day)
            if jump:
                self._add('jump-%s-%s' % (emp.id, day), 'jump', '2', 65, emp,
                          _('%(e)s impossible movement on %(d)s', e=emp.name, d=day),
                          _('%s GPS jumps faster than 160 km/h were detected.') % jump, day)

    def _scan_attendance(self, since):
        Att = self.env['hr.attendance'].sudo()
        for a in Att.search([('check_in', '>=', datetime.combine(since, datetime.min.time())),
                             ('nl_geo_status', '=', 'outside')]):
            self._add('outside-%s' % a.id, 'outside_site', '2', 60, a.employee_id,
                      _('%s punched in outside the work site', a.employee_id.name),
                      _('%d m away from the nearest allowed site.') % round(a.nl_in_distance_m),
                      a.check_in.date(), a)

    def _scan_expenses(self, since):
        Line = self.env['conveyance.sheet.line'].sudo()
        for l in Line.search([('date', '>=', since), ('nl_geo_status', 'in', ('mismatch', 'suspicious'))]):
            self._add('geo-%s' % l.id, 'geo_mismatch', '3' if l.nl_geo_status == 'suspicious' else '2',
                      80 if l.nl_geo_status == 'suspicious' else 70, l.nl_employee_id,
                      _('%(e)s: claim not supported by map (%(d)s)', e=l.nl_employee_id.name, d=l.date),
                      l.nl_geo_note or '', l.date, l.sheet_id)
        for l in Line.search([('date', '>=', since), ('nl_dup_bill', '=', True)]):
            self._add('dup-%s' % l.id, 'dup_bill', '3', 85, l.nl_employee_id,
                      _('%(e)s: bill image already used elsewhere', e=l.nl_employee_id.name),
                      _('The same bill image appears on more than one expense line.'), l.date, l.sheet_id)
        # abnormal amounts: z-score vs the employee's own last 90 days (needs >= 8 samples)
        hist_from = fields.Date.today() - timedelta(days=90)
        for l in Line.search([('date', '>=', since), ('total_amount', '>', 0)]):
            hist = Line.search([('nl_employee_id', '=', l.nl_employee_id.id), ('date', '>=', hist_from),
                                ('id', '!=', l.id)]).mapped('total_amount')
            if len(hist) < 8:
                continue
            mu, sd = statistics.mean(hist), statistics.pstdev(hist) or 1.0
            z = (l.total_amount - mu) / sd
            if z > 3 and l.total_amount > mu * 2:
                self._add('amt-%s' % l.id, 'abnormal_amount', '2', min(95, int(50 + z * 8)), l.nl_employee_id,
                          _('%(e)s: unusually high claim %(a).0f', e=l.nl_employee_id.name, a=l.total_amount),
                          _('Usual line amount is about %(m).0f (z-score %(z).1f).', m=mu, z=z), l.date, l.sheet_id)

    def _scan_patterns(self):
        today = fields.Date.today()
        start = datetime.combine(today - timedelta(days=14), datetime.min.time())
        Att = self.env['hr.attendance'].sudo()
        # late arrivals: check-in after 10:00 local on >= 5 of last 14 days
        by_emp = {}
        for a in Att.search([('check_in', '>=', start)]):
            # cron runs without a user time zone -> use the employee's own zone, else 10:00 UTC would be 16:00 in Dhaka
            local = fields.Datetime.context_timestamp(
                a.with_context(tz=a.employee_id.tz or self.env.user.tz or 'UTC'), a.check_in)
            if local.hour >= LATE_HOUR:
                by_emp.setdefault(a.employee_id, set()).add(local.date())
        for emp, days in by_emp.items():
            if len(days) >= 5:
                self._add('late-%s-%s' % (emp.id, today.isocalendar()[1]), 'late_pattern', '1', 40, emp,
                          _('%s arrived after 10:00 on %d of the last 14 days', emp.name, len(days)),
                          _('Review attendance pattern.'), today)
        # offline gaps
        Pres = self.env['nelsis.presence.log'].sudo()
        for emp, n in Pres._read_group([('state', '=', 'offline'), ('log_date', '>=', today - timedelta(days=7))],
                                       ['employee_id'], ['__count']):
            if n >= 15:
                self._add('off-%s-%s' % (emp.id, today.isocalendar()[1]), 'offline_pattern', '1', 35, emp,
                          _('%s went offline %d times this week', emp.name, n),
                          _('Frequent offline periods can mean app killed by battery saver or deliberate switching off.'), today)

    # ---------------------------------------------------------------- digest
    @api.model
    def daily_digest(self):
        day = fields.Date.today() - timedelta(days=1)
        Insight = self.env['nelsis.ai.insight'].sudo()
        fp = 'digest-%s' % day
        if Insight.search_count([('fingerprint', '=', fp)]):
            return
        Att = self.env['hr.attendance'].sudo()
        start = datetime.combine(day, datetime.min.time())
        atts = Att.search([('check_in', '>=', start), ('check_in', '<', start + timedelta(days=1))])
        new = Insight.search([('date', '>=', day), ('kind', '!=', 'digest')])
        high = new.filtered(lambda i: i.severity == '3')
        facts = (
            'Date: %s\nEmployees present: %d\nTotal worked hours: %.1f\nNew risk findings: %d (high: %d)\n'
            'Findings:\n%s' % (day, len(atts.mapped('employee_id')), sum(atts.mapped('worked_hours')),
                               len(new), len(high), '\n'.join('- [%s] %s' % (i.severity, i.name) for i in new[:25])))
        text = Insight._llm_raw(
            'You write a concise daily operations digest for a field-force administrator. '
            'Use 5 short bullets max: attendance, risks to review first, positive notes. No fluff.', facts)
        if not text:          # no API key, or the service is down: the plain facts are still useful
            text = facts
        Insight.create({'fingerprint': fp, 'kind': 'digest', 'severity': '0', 'name': _('Daily digest %s') % day,
                        'description': facts, 'ai_explanation': text, 'date': day})


class NelsisDashboardExtension(models.AbstractModel):
    _inherit = 'nelsis.dashboard.extension'

    @api.model
    def dashboard_extra(self, employees, date_from, date_to):
        res = super().dashboard_extra(employees, date_from, date_to)
        I = self.env['nelsis.ai.insight']
        dom = [('employee_id', 'in', employees.ids), ('kind', '!=', 'digest')]
        res['ai_kpis'] = {
            'open': I.search_count(dom + [('state', '=', 'open')]),
            'high': I.search_count(dom + [('state', '=', 'open'), ('severity', '=', '3')]),
        }
        return res
