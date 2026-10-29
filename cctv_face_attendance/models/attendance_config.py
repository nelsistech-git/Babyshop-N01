# -*- coding: utf-8 -*-
"""Single place that knows every face-attendance setting, its default and how to read it."""
import hashlib
import json

from odoo import _, api, fields, models

PREFIX = 'cctv_management.attendance_'

# key -> (default, cast).  Used by the engine, the settings screen and the API.
DEFAULTS = {
    # --- decided in Odoo
    'min_confidence': (55.0, float),        # % at/above which a punch is made automatically
    'review_confidence': (45.0, float),     # % at/above which HR is asked to approve
    'min_gap_seconds': (60, int),
    'min_stay_minutes': (5, int),
    'both_gap_minutes': (10, int),
    'stale_open_hours': (16, int),
    'max_age_minutes': (30, int),
    'snapshot_retention_days': (90, int),
    'event_confirm_count': (3, int),
    'event_confirm_seconds': (15, int),
    'require_consent': (False, bool),
    'log_ignored': (False, bool),
    'alert_unknown': (False, bool),
    'skip_employee_photo': (False, bool),
    'disable_event_api': (False, bool),
    # --- enforced by the face service (sent to it in /config)
    'margin': (0.08, float),
    'confirm_frames': (3, int),
    'confirm_seconds': (6, int),
    'min_face_px': (70, int),
    'min_det_score': (0.65, float),
    'min_sharpness': (30.0, float),
    'cooldown_seconds': (30, int),
}
SERVICE_KEYS = ('margin', 'confirm_frames', 'confirm_seconds', 'min_face_px', 'min_det_score',
                'min_sharpness', 'cooldown_seconds', 'min_confidence', 'review_confidence')


class CctvAttendanceConfig(models.AbstractModel):
    _name = 'cctv.attendance.config'
    _description = 'Face attendance settings helper'

    @api.model
    def param(self, key):
        default, cast = DEFAULTS[key]
        raw = self.env['ir.config_parameter'].sudo().get_param(PREFIX + key)
        if raw in (None, False, ''):
            return default
        try:
            if cast is bool:
                return str(raw).strip().lower() in ('1', 'true', 'yes')
            return cast(raw)
        except (TypeError, ValueError):
            return default

    @api.model
    def service_settings(self):
        return {k: self.param(k) for k in SERVICE_KEYS}

    @api.model
    def bump_version(self):
        self.env['ir.config_parameter'].sudo().set_param(
            PREFIX + 'bump', fields.Datetime.to_string(fields.Datetime.now()))

    @api.model
    def _bump(self):
        return self.env['ir.config_parameter'].sudo().get_param(PREFIX + 'bump') or ''

    @api.model
    def version_of(self, payload):
        blob = json.dumps(payload, sort_keys=True, default=str) + self._bump()
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    @api.model
    def readiness_text(self):
        cams = self.env['cctv.camera'].sudo().search([('ai_attendance', '=', True)])
        persons = self.env['cctv.person'].sudo().search([('person_type', '=', 'employee')])
        employees = self.env['hr.employee'].sudo().search_count([])
        enrolled = persons.filtered(lambda p: p.employee_id and p.attendance_enabled)
        lines = [_('%(n)s attendance camera(s): %(r)s running.',
                   n=len(cams), r=len(cams.filtered(lambda c: c.attendance_state == 'running')))]
        lines.append(_('%(a)s of %(b)s employees are enrolled for face attendance.', a=len(enrolled), b=employees))
        bad = enrolled.filtered(lambda p: p.attendance_enroll_state in ('no_face', 'low_quality', 'multiple'))
        if bad:
            lines.append('• ' + _('%s enrolled employee(s) have a photo the service cannot use '
                                  '(see Face Attendance > Enrolment Status).') % len(bad))
        if self.param('require_consent'):
            n = len(enrolled.filtered(lambda p: not p.biometric_consent))
            if n:
                lines.append('• ' + _('%s enrolled employee(s) are excluded: no biometric consent recorded.') % n)
        if not cams:
            lines.append('• ' + _('No camera is marked for attendance yet (Configuration > Cameras).'))
        if not self.env['ir.config_parameter'].sudo().get_param('cctv_management.api_key'):
            lines.append('• ' + _('System parameter cctv_management.api_key is not set: the service cannot connect.'))
        return '\n'.join(lines)
