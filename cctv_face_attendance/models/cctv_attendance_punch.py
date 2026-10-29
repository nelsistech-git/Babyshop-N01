# -*- coding: utf-8 -*-
"""Punch log + the engine that turns a recognised face into an hr.attendance record."""
import logging
from datetime import timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..utils import attendance_policy as policy

_logger = logging.getLogger(__name__)
LOCK_NAMESPACE = 7312


class CctvAttendancePunch(models.Model):
    _name = 'cctv.attendance.punch'
    _description = 'CCTV Face Attendance Punch'
    _order = 'punch_time desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name')
    employee_id = fields.Many2one('hr.employee', required=True, index=True, ondelete='cascade')
    person_id = fields.Many2one('cctv.person', ondelete='set null', index=True)
    camera_id = fields.Many2one('cctv.camera', required=True, ondelete='cascade', index=True)
    office_id = fields.Many2one(related='camera_id.office_id', store=True)
    company_id = fields.Many2one(related='camera_id.company_id', store=True)
    punch_time = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    confidence = fields.Float(string='Match (%)')
    sightings = fields.Integer(default=1, help='How many frames agreed on this person before the punch.')
    result = fields.Selection([
        ('check_in', 'Checked In'), ('check_out', 'Checked Out'), ('review', 'Needs Review'),
        ('ignored', 'Ignored'), ('dismissed', 'Dismissed'), ('error', 'Error'),
    ], required=True, default='ignored', index=True)
    reason = fields.Char()
    source = fields.Selection([
        ('cctv_service', 'Face service'), ('event_api', 'AI event API'), ('manual', 'Approved by HR'),
    ], default='cctv_service')
    snapshot = fields.Binary(attachment=True)
    attendance_id = fields.Many2one('hr.attendance', ondelete='set null', index=True)
    reviewed_by = fields.Many2one('res.users', readonly=True)
    reviewed_on = fields.Datetime(readonly=True)
    is_old = fields.Boolean(help='Arrived much later than it happened (service was offline).')

    @api.depends('employee_id', 'result', 'punch_time')
    def _compute_display_name(self):
        labels = dict(self._fields['result'].selection)
        for rec in self:
            rec.display_name = '%s - %s (%s)' % (rec.employee_id.name or '', labels.get(rec.result, ''),
                                                 rec.punch_time or '')

    # ================================================================== engine
    @api.model
    def register_sighting(self, camera, person, confidence, when=None, snapshot=None,
                          source='cctv_service', sightings=1, face_log=None):
        """Entry point for every recognised face on an attendance camera.

        Returns the cctv.attendance.punch row that was written, or an empty recordset when the
        sighting was not worth recording (not an attendance camera, ignored by the rules, ...).
        """
        self = self.sudo()      # called by the public API / AI hooks: the engine always runs privileged
        cfg = self.env['cctv.attendance.config']
        camera, person = camera.sudo(), person.sudo()
        empty = self.browse()
        if not camera.ai_attendance:
            return empty
        employee = person.employee_id.sudo()
        why = person._attendance_ineligible_reason()
        if not why and employee.company_id and camera.company_id and employee.company_id != camera.company_id:
            why = _('employee belongs to another company')
        if why:
            return self._log_ignored(employee, person, camera, confidence, when, why, source, snapshot)

        band = policy.classify_confidence(confidence, cfg.param('min_confidence'), cfg.param('review_confidence'))
        if band == policy.REJECT:
            return empty

        now = fields.Datetime.now()
        when, is_old = policy.normalize_time(when, now, cfg.param('max_age_minutes'))

        # one decision at a time per employee, even with several cameras / worker threads
        self.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', (LOCK_NAMESPACE, employee.id))
        last = self.env['hr.attendance'].sudo().search(
            [('employee_id', '=', employee.id)], order='check_in desc, id desc', limit=1)
        action, reason = self._decide(camera, last, when)

        if action == policy.IGNORE:
            return self._log_ignored(employee, person, camera, confidence, when, reason, source, snapshot)

        vals = {
            'employee_id': employee.id, 'person_id': person.id, 'camera_id': camera.id,
            'punch_time': when, 'confidence': confidence, 'sightings': sightings,
            'source': source, 'snapshot': snapshot or False, 'is_old': is_old,
        }
        if band == policy.REVIEW or is_old:
            return self._queue_review(vals, action, reason, band, is_old)

        punch = self.create(dict(vals, result='check_out' if action == policy.CHECK_OUT else 'check_in',
                                 reason=reason))
        self._apply(punch, action, last)
        if face_log and punch.result in ('check_in', 'check_out'):
            face_log.sudo().write({'linked_to_attendance': True})
        return punch

    @api.model
    def _decide(self, camera, last, when):
        cfg = self.env['cctv.attendance.config']
        is_in = bool(last and not last.check_out)
        last_time = (last.check_out or last.check_in) if last else None
        return policy.decide(
            camera.attendance_direction or 'in', is_in, last.check_in if is_in else None, last_time, when,
            min_gap_seconds=cfg.param('min_gap_seconds'), min_stay_minutes=cfg.param('min_stay_minutes'),
            both_gap_minutes=cfg.param('both_gap_minutes'), stale_open_hours=cfg.param('stale_open_hours'))

    @api.model
    def _log_ignored(self, employee, person, camera, confidence, when, reason, source, snapshot):
        if not self.env['cctv.attendance.config'].param('log_ignored') or not employee:
            return self.browse()
        return self.create({
            'employee_id': employee.id, 'person_id': person.id, 'camera_id': camera.id,
            'punch_time': when or fields.Datetime.now(), 'confidence': confidence,
            'result': 'ignored', 'reason': reason, 'source': source, 'snapshot': snapshot or False})

    @api.model
    def _queue_review(self, vals, action, reason, band, is_old):
        """Borderline / late punches wait for HR instead of silently changing attendance."""
        recent = self.search([
            ('employee_id', '=', vals['employee_id']), ('result', '=', 'review'),
            ('create_date', '>=', fields.Datetime.now() - timedelta(minutes=10))], limit=1)
        if recent:
            return recent
        verb = _('check out') if action == policy.CHECK_OUT else _('check in')
        why = _('late punch (arrived long after it happened)') if is_old else _(
            'match %(c).0f%% is below the automatic limit', c=vals['confidence'])
        punch = self.create(dict(vals, result='review', reason=_('Would %(v)s - %(w)s', v=verb, w=why)))
        camera = punch.camera_id
        self.env['cctv.alert'].sudo().create({
            'name': _('Face attendance needs review: %(e)s at %(c)s', e=punch.employee_id.name, c=camera.name),
            'alert_type': 'other', 'severity': 'low', 'camera_id': camera.id, 'office_id': camera.office_id.id})
        return punch

    @api.model
    def _apply(self, punch, action, last):
        """Write the attendance for an accepted punch; on a rule violation keep the punch as 'error'."""
        employee, camera, when = punch.employee_id, punch.camera_id, punch.punch_time
        Attendance = self.env['hr.attendance'].sudo()
        try:
            with self.env.cr.savepoint():
                if action == policy.CLOSE_STALE_AND_CHECK_IN:
                    self._close_stale(last, when)
                    action = policy.CHECK_IN
                if action == policy.CHECK_IN:
                    late, is_late = self._late_info(employee, when)
                    att = Attendance.create({
                        'employee_id': employee.id, 'check_in': when, 'in_mode': 'cctv_face',
                        'cctv_in_camera_id': camera.id, 'cctv_in_confidence': punch.confidence,
                        'cctv_in_snapshot': punch.snapshot, 'cctv_in_punch_id': punch.id,
                        'cctv_late_minutes': late, 'cctv_is_late': is_late,
                    })
                    punch.write({'attendance_id': att.id, 'result': 'check_in'})
                elif action == policy.CHECK_OUT:
                    last.write({
                        'check_out': when, 'out_mode': 'cctv_face', 'cctv_out_camera_id': camera.id,
                        'cctv_out_confidence': punch.confidence, 'cctv_out_snapshot': punch.snapshot,
                        'cctv_out_punch_id': punch.id})
                    punch.write({'attendance_id': last.id, 'result': 'check_out'})
        except (ValidationError, UserError) as exc:
            _logger.warning('Face attendance rejected by hr_attendance for %s: %s', employee.name, exc)
            punch.write({'result': 'error', 'reason': str(exc.args[0] if exc.args else exc)})
        return punch

    @api.model
    def _close_stale(self, attendance, when):
        """Forgotten check-out: close at the last time the person was seen (never at 'now')."""
        seen = self.env['cctv.face.log'].sudo().search([
            ('person_id.employee_id', '=', attendance.employee_id.id),
            ('detected_at', '>', attendance.check_in),
            ('detected_at', '<', when - timedelta(minutes=10))], order='detected_at desc', limit=1)
        out = max(seen.detected_at, attendance.check_in) if seen else attendance.check_in
        attendance.write({'check_out': out, 'cctv_auto_closed': True, 'out_mode': 'cctv_face'})

    @api.model
    def _late_info(self, employee, when):
        """(minutes after shift start, is_late) from the CCTV monitoring assignment; (0, False) if none."""
        mon = self.env['cctv.employee.monitor'].sudo().search(
            [('employee_id', '=', employee.id), ('monitoring_active', '=', True)], limit=1)
        if not mon:
            return 0.0, False
        try:
            local_day = pytz.utc.localize(when).astimezone(mon._get_tz()).date()
            if not getattr(mon, 'work_' + local_day.strftime('%a').lower(), True):
                return 0.0, False
            start, end = mon._shift_window(local_day)
            if when >= end:
                return 0.0, False
            earlier = self.env['hr.attendance'].sudo().search_count([
                ('employee_id', '=', employee.id), ('check_in', '>=', start - timedelta(hours=2)),
                ('check_in', '<', when)])
            if earlier:
                return 0.0, False
            late = max(0.0, (when - start).total_seconds() / 60.0)
            return round(late, 1), late > (mon.grace_minutes or 0)
        except Exception:
            _logger.exception('Could not compute lateness for %s', employee.name)
            return 0.0, False

    # ================================================================== HR review
    def action_approve(self):
        self = self.sudo()
        for punch in self.filtered(lambda p: p.result == 'review'):
            self.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', (LOCK_NAMESPACE, punch.employee_id.id))
            last = self.env['hr.attendance'].sudo().search(
                [('employee_id', '=', punch.employee_id.id)], order='check_in desc, id desc', limit=1)
            action, reason = self._decide(punch.camera_id, last, punch.punch_time)
            punch.write({'reviewed_by': self.env.uid, 'reviewed_on': fields.Datetime.now(), 'source': 'manual'})
            if action == policy.IGNORE:
                punch.write({'result': 'ignored', 'reason': _('Approved, but nothing to do: %s', reason)})
            else:
                punch.write({'reason': reason})
                self._apply(punch, action, last)
        return True

    def action_dismiss(self):
        self.filtered(lambda p: p.result == 'review').write({
            'result': 'dismissed', 'reviewed_by': self.env.uid, 'reviewed_on': fields.Datetime.now()})
        return True

    # ================================================================== crons
    @api.model
    def cron_close_stale_attendance(self):
        """Close face-created attendances that were never checked out (employee left unseen)."""
        hours = self.env['cctv.attendance.config'].param('stale_open_hours')
        if not hours:
            return
        cutoff = fields.Datetime.now() - timedelta(hours=hours)
        for att in self.env['hr.attendance'].sudo().search([
                ('check_out', '=', False), ('check_in', '<', cutoff), ('in_mode', '=', 'cctv_face')]):
            try:
                with self.env.cr.savepoint():
                    self._close_stale(att, fields.Datetime.now())
            except (ValidationError, UserError):
                _logger.exception('Could not auto-close attendance %s', att.id)

    @api.model
    def cron_purge_snapshots(self):
        """Evidence images are biometric data: drop them after the retention period (rows stay)."""
        days = self.env['cctv.attendance.config'].param('snapshot_retention_days')
        if not days:
            return
        cutoff = fields.Datetime.now() - timedelta(days=days)
        self.sudo().search([('punch_time', '<', cutoff), ('snapshot', '!=', False)]).write({'snapshot': False})
        self.env['hr.attendance'].sudo().search([
            ('check_in', '<', cutoff), '|', ('cctv_in_snapshot', '!=', False),
            ('cctv_out_snapshot', '!=', False)]).write({'cctv_in_snapshot': False, 'cctv_out_snapshot': False})
