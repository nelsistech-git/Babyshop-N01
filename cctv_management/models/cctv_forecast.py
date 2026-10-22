# -*- coding: utf-8 -*-
"""AI Insights & Forecasting (SRS feature 11).

cctv.forecast  - hourly visitor-volume forecast per site, with an 80% range,
                 a confidence score and a plain-language evidence trail.
cctv.insight   - generated findings (peak hours, branch comparison, traffic
                 anomalies, recurring security events, forecast peaks) each
                 with a confidence level and the evidence behind it.

The statistics live in utils/forecast_engine.py (pure Python, unit-testable).
Everything here is a transparent statistical baseline built from the data in
cctv.footfall.count / cctv.event - not a black-box ML model.
"""
import logging
from collections import Counter
from datetime import datetime, timedelta

import pytz

from odoo import api, fields, models

from ..utils import forecast_engine as fe

_logger = logging.getLogger(__name__)


def _utc_now():
    return fields.Datetime.now()   # naive UTC


class CctvForecast(models.Model):
    _name = 'cctv.forecast'
    _description = 'Visitor Volume Forecast (hourly)'
    _order = 'target_time asc, office_id'

    office_id = fields.Many2one('cctv.office', required=True, ondelete='cascade', index=True)
    target_time = fields.Datetime(required=True, index=True, help='Start of the forecast hour (UTC).')
    target_local = fields.Char(string='Local Hour', help='Start of the forecast hour in the reporting timezone.')
    predicted_entries = fields.Float(string='Predicted Entries')
    lower_bound = fields.Float(string='Low (80% range)')
    upper_bound = fields.Float(string='High (80% range)')
    confidence = fields.Float(string='Confidence (%)')
    sample_count = fields.Integer(string='Comparable Weeks Used')
    method = fields.Char(default='seasonal_weekday_hour')
    evidence = fields.Text(string='Why this forecast')
    generated_at = fields.Datetime(default=_utc_now)
    actual_known = fields.Boolean(default=False)
    actual_entries = fields.Float(string='Actual Entries')
    abs_error_pct = fields.Float(string='Abs. Error (%)')

    # ---------------------------------------------------------------- helpers
    @api.model
    def _tz(self):
        name = (self.env['ir.config_parameter'].sudo().get_param('cctv_management.report_timezone')
                or self.env.user.tz or 'UTC')
        try:
            return pytz.timezone(name)
        except pytz.UnknownTimeZoneError:
            return pytz.utc

    @api.model
    def _now_local(self):
        return pytz.utc.localize(_utc_now()).astimezone(self._tz()).replace(tzinfo=None)

    @api.model
    def _to_utc_naive(self, local_naive):
        return self._tz().localize(local_naive, is_dst=False).astimezone(pytz.utc).replace(tzinfo=None)

    @api.model
    def _hourly_history(self, office_id, weeks=9):
        """{naive local hour: total entries} for one site (all counting cameras)."""
        since = _utc_now() - timedelta(weeks=weeks)
        tzname = self._tz().zone
        self.env.cr.execute("""
            SELECT date_trunc('hour', (interval_start AT TIME ZONE 'UTC') AT TIME ZONE %s) AS h,
                   COALESCE(SUM(entry_count), 0)
              FROM cctv_footfall_count
             WHERE office_id = %s AND interval_start >= %s
          GROUP BY 1
        """, (tzname, office_id, since))
        return {row[0]: float(row[1]) for row in self.env.cr.fetchall()}

    # ------------------------------------------------------------------ crons
    @api.model
    def cron_generate_forecasts(self, horizon_hours=168):
        now_local = self._now_local()
        start = now_local.replace(minute=0, second=0, microsecond=0)
        utc_now = _utc_now()
        offices = self.env['cctv.office'].search([])
        created = 0
        for office in offices:
            hourly = self._hourly_history(office.id)
            if not hourly:
                continue
            trend = fe.trend_factor(hourly, now_local)
            vals_list = []
            for h in range(1, int(horizon_hours) + 1):
                target_local = start + timedelta(hours=h)
                res = fe.forecast_hour(hourly, target_local, now_local, trend=trend)
                if not res:
                    continue
                vals_list.append({
                    'office_id': office.id,
                    'target_time': self._to_utc_naive(target_local),
                    'target_local': target_local.strftime('%a %d %b %H:00'),
                    'predicted_entries': res['predicted'],
                    'lower_bound': res['lower'],
                    'upper_bound': res['upper'],
                    'confidence': res['confidence'],
                    'sample_count': res['sample_count'],
                    'evidence': res['evidence'],
                    'generated_at': utc_now,
                })
            # replace only the not-yet-happened forecasts; past ones are kept for accuracy tracking
            self.search([('office_id', '=', office.id), ('target_time', '>', utc_now)]).unlink()
            if vals_list:
                self.create(vals_list)
                created += len(vals_list)
        _logger.info('CCTV forecast: created %s hourly forecasts', created)
        return created

    @api.model
    def cron_update_actuals(self):
        """Fill in what really happened for forecast hours that are over, and the error."""
        cutoff = _utc_now() - timedelta(hours=1)
        pending = self.search([('actual_known', '=', False), ('target_time', '<', cutoff)])
        for office in pending.mapped('office_id'):
            recs = pending.filtered(lambda r: r.office_id == office)
            lo, hi = min(recs.mapped('target_time')), max(recs.mapped('target_time')) + timedelta(hours=1)
            self.env.cr.execute("""
                SELECT date_trunc('hour', interval_start), COALESCE(SUM(entry_count), 0)
                  FROM cctv_footfall_count
                 WHERE office_id = %s AND interval_start >= %s AND interval_start < %s
              GROUP BY 1
            """, (office.id, lo, hi))
            actual = {r[0]: float(r[1]) for r in self.env.cr.fetchall()}
            for rec in recs:
                if rec.target_time not in actual:
                    continue   # no counting data for that hour (camera offline?) - leave unknown
                a = actual[rec.target_time]
                rec.write({
                    'actual_known': True, 'actual_entries': a,
                    'abs_error_pct': abs(rec.predicted_entries - a) / max(a, 1.0) * 100.0,
                })

    @api.model
    def get_accuracy(self, office_id, days=14, min_actual=5):
        """Mean absolute percentage error over recent forecasts (hours with >= min_actual entries)."""
        since = _utc_now() - timedelta(days=days)
        recs = self.search([('office_id', '=', office_id), ('actual_known', '=', True),
                            ('target_time', '>=', since), ('actual_entries', '>=', min_actual)])
        if len(recs) < 6:
            return None, len(recs)
        return sum(recs.mapped('abs_error_pct')) / len(recs), len(recs)


class CctvInsight(models.Model):
    _name = 'cctv.insight'
    _description = 'AI Insight (with confidence and evidence)'
    _order = 'generated_at desc, id desc'

    name = fields.Char(required=True)
    insight_type = fields.Selection([
        ('peak_hours', 'Peak Visitor Hours'),
        ('branch_comparison', 'Branch Comparison'),
        ('traffic_anomaly', 'Unusual Traffic Day'),
        ('recurring_event', 'Recurring Security Event'),
        ('forecast_peak', 'Forecast: Upcoming Peak'),
        ('forecast_accuracy', 'Forecast Accuracy'),
    ], required=True, index=True)
    severity = fields.Selection([('info', 'Info'), ('notice', 'Notice'), ('warning', 'Warning')],
                                default='info')
    office_id = fields.Many2one('cctv.office', ondelete='cascade')
    camera_id = fields.Many2one('cctv.camera', ondelete='cascade')
    summary = fields.Text()
    evidence = fields.Text(string='Evidence (how this was derived)')
    confidence = fields.Float(string='Confidence (%)')
    period_start = fields.Datetime()
    period_end = fields.Datetime()
    generated_at = fields.Datetime(default=_utc_now)
    active = fields.Boolean(default=True)

    # ------------------------------------------------------------- generation
    @api.model
    def _publish(self, insight_type, office, name, summary, evidence, confidence,
                 severity='info', camera=None, period=None):
        old = self.search([('insight_type', '=', insight_type), ('office_id', '=', office.id if office else False),
                           ('camera_id', '=', camera.id if camera else False), ('name', '=', name)])
        old.write({'active': False})
        vals = {'name': name, 'insight_type': insight_type, 'severity': severity,
                'office_id': office.id if office else False, 'camera_id': camera.id if camera else False,
                'summary': summary, 'evidence': evidence, 'confidence': round(confidence, 1)}
        if period:
            vals['period_start'], vals['period_end'] = period
        return self.create(vals)

    @api.model
    def cron_generate_insights(self):
        Forecast = self.env['cctv.forecast']
        now_local = Forecast._now_local()
        utc_now = _utc_now()
        offices = self.env['cctv.office'].search([])
        week_totals = {}
        for office in offices:
            hourly = Forecast._hourly_history(office.id)
            if not hourly:
                continue
            self._insight_peak_hours(office, hourly, now_local)
            self._insight_traffic_anomaly(office, hourly, now_local)
            week_totals[office] = self._week_total(hourly, now_local)
            self._insight_forecast_peak(office, utc_now)
            self._insight_forecast_accuracy(office)
        self._insight_branch_comparison(week_totals, now_local)
        self._insight_recurring_events(utc_now, Forecast)
        return True

    @staticmethod
    def _week_total(hourly, now_local, days=7):
        end = now_local.replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(days=days)
        days_with_data = {k.date() for k in hourly if start <= k < end}
        return sum(v for k, v in hourly.items() if start <= k < end), len(days_with_data)

    @api.model
    def _insight_peak_hours(self, office, hourly, now_local):
        ranked, n_days = fe.peak_hours(hourly, top=3, days=28, now_local=now_local)
        if not ranked or n_days < 3:
            return
        txt = ', '.join('%02d:00 (avg %.0f entries/h)' % (h, v) for h, v in ranked)
        self._publish(
            'peak_hours', office, 'Peak hours at %s' % office.name,
            'Busiest hours: %s.' % txt,
            'Average entries per hour-of-day over the last 28 days, using %d day(s) with counting data. '
            'Ranked by mean entries; sums all counting cameras at the site.' % n_days,
            fe.confidence_from_days(n_days),
            period=(_utc_now() - timedelta(days=28), _utc_now()))

    @api.model
    def _insight_traffic_anomaly(self, office, hourly, now_local):
        """Yesterday's total vs the same weekday in the previous 4 weeks."""
        yday = (now_local - timedelta(days=1)).date()

        def day_total(d):
            vals = [v for k, v in hourly.items() if k.date() == d]
            return sum(vals) if vals else None
        actual = day_total(yday)
        past = [day_total(yday - timedelta(weeks=w)) for w in range(1, 5)]
        past = [p for p in past if p is not None]
        if actual is None or len(past) < 3:
            return
        mean = sum(past) / len(past)
        if mean < 20:
            return
        dev = (actual - mean) / mean * 100.0
        if abs(dev) < 30:
            return
        std = (sum((p - mean) ** 2 for p in past) / len(past)) ** 0.5
        z = abs(actual - mean) / std if std > 0 else 3.0
        self._publish(
            'traffic_anomaly', office,
            '%s traffic %s on %s' % (office.name, 'spike' if dev > 0 else 'drop', yday.strftime('%a %d %b')),
            'Entries were %d vs a typical %.0f for this weekday (%+.0f%%).' % (actual, mean, dev),
            'Compared with the same weekday in the previous %d weeks: %s (mean %.0f, std dev %.0f, z-score %.1f). '
            'Check for promotions, closures, holidays or a camera/counting fault before drawing conclusions.' % (
                len(past), ', '.join('%d' % p for p in past), mean, std, z),
            min(90.0, 40.0 + 12.0 * z), severity='notice' if dev > 0 else 'warning')

    @api.model
    def _insight_forecast_peak(self, office, utc_now):
        rows = self.env['cctv.forecast'].search(
            [('office_id', '=', office.id), ('target_time', '>', utc_now),
             ('target_time', '<=', utc_now + timedelta(days=7))])
        if not rows:
            return
        top = max(rows, key=lambda r: r.predicted_entries)
        if top.predicted_entries <= 0:
            return
        self._publish(
            'forecast_peak', office, 'Expected peak next 7 days at %s' % office.name,
            'Busiest forecast hour: %s, about %.0f entries (80%% range %.0f-%.0f).' % (
                top.target_local, top.predicted_entries, top.lower_bound, top.upper_bound),
            top.evidence, top.confidence)

    @api.model
    def _insight_forecast_accuracy(self, office):
        mape, n = self.env['cctv.forecast'].get_accuracy(office.id)
        if mape is None:
            return
        self._publish(
            'forecast_accuracy', office, 'Forecast accuracy at %s' % office.name,
            'Average forecast error over the last 14 days: %.0f%% (%d hours compared).' % (mape, n),
            'Mean absolute percentage error between predicted and actual hourly entries, only for hours '
            'with at least 5 real entries. Lower is better; above ~40%% means the history is too noisy '
            'or too short to rely on.', max(10.0, min(95.0, 100.0 - mape)),
            severity='warning' if mape > 40 else 'info')

    @api.model
    def _insight_branch_comparison(self, week_totals, now_local):
        usable = {o: t for o, (t, d) in week_totals.items() if d >= 3}
        if len(usable) < 2:
            return
        avg = sum(usable.values()) / len(usable)
        if avg <= 0:
            return
        ranked = sorted(usable.items(), key=lambda x: x[1], reverse=True)
        lines = ['%s: %d entries (%+.0f%% vs network average)' % (o.name, t, (t - avg) / avg * 100.0)
                 for o, t in ranked]
        min_days = min(d for o, (t, d) in week_totals.items() if o in usable)
        self._publish(
            'branch_comparison', False, 'Branch footfall comparison (last 7 days)',
            '%s leads, %s trails.' % (ranked[0][0].name, ranked[-1][0].name),
            'Total entries per site over the last 7 days; network average %.0f.\n%s\n'
            'Sites differ in size, opening hours and number of counting cameras - compare trends, '
            'not just totals.' % (avg, '\n'.join(lines)),
            fe.confidence_from_days(min_days, 7))

    @api.model
    def _insight_recurring_events(self, utc_now, Forecast):
        since = utc_now - timedelta(days=30)
        groups = self.env['cctv.event'].read_group(
            [('event_time', '>=', since), ('behavior_type', 'not in', ['none', False])],
            ['camera_id', 'behavior_type'], ['camera_id', 'behavior_type'], lazy=False)
        groups = sorted([g for g in groups if g['__count'] >= 5], key=lambda g: g['__count'], reverse=True)[:10]
        tz = Forecast._tz()
        for g in groups:
            cam = self.env['cctv.camera'].browse(g['camera_id'][0])
            events = self.env['cctv.event'].search(g['__domain'], limit=500)
            local = [pytz.utc.localize(e.event_time).astimezone(tz) for e in events if e.event_time]
            if not local:
                continue
            days = {t.date() for t in local}
            hours = Counter(t.hour for t in local)
            top_hour, top_n = hours.most_common(1)[0]
            share = top_n / len(local) * 100.0
            if len(days) < 3 and share < 50:
                continue
            label = dict(events[0]._fields['behavior_type'].selection).get(g['behavior_type'], g['behavior_type'])
            self._publish(
                'recurring_event', cam.office_id,
                '%s repeatedly at %s' % (label, cam.name),
                '%d events in 30 days on %d different days; %.0f%% happened around %02d:00.' % (
                    len(local), len(days), share, top_hour),
                'Counted cctv.event rows for this camera and behavior over the last 30 days '
                '(up to 500 most recent). Hour distribution (local time): %s. '
                'Recurring flags usually mean a process or placement issue (or a mis-tuned rule), '
                'not necessarily misconduct - review the footage.' % (
                    ', '.join('%02d:00=%d' % (h, c) for h, c in sorted(hours.items()))),
                fe.confidence_from_days(len(days), 14), severity='notice', camera=cam,
                period=(since, utc_now))
