# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .attendance_config import DEFAULTS, PREFIX


def _f(key, cls, string, **kw):
    default = DEFAULTS[key][0]
    return cls(string=string, config_parameter=PREFIX + key, default=default, **kw)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cctv_att_min_confidence = _f('min_confidence', fields.Float, 'Punch automatically at or above (%)')
    cctv_att_review_confidence = _f('review_confidence', fields.Float, 'Ask HR to review at or above (%)')
    cctv_att_margin = _f('margin', fields.Float, 'Gap to the next-best person')
    cctv_att_confirm_frames = _f('confirm_frames', fields.Integer, 'Frames that must agree')
    cctv_att_confirm_seconds = _f('confirm_seconds', fields.Integer, 'Frames must agree within (s)')
    cctv_att_min_face_px = _f('min_face_px', fields.Integer, 'Smallest face (pixels)')
    cctv_att_min_det_score = _f('min_det_score', fields.Float, 'Face detector score')
    cctv_att_min_sharpness = _f('min_sharpness', fields.Float, 'Sharpness')
    cctv_att_cooldown_seconds = _f('cooldown_seconds', fields.Integer, 'Re-send same person after (s)')
    cctv_att_min_gap_seconds = _f('min_gap_seconds', fields.Integer, 'Minimum gap between punches (s)')
    cctv_att_min_stay_minutes = _f('min_stay_minutes', fields.Integer, 'Earliest check-out after check-in (min)')
    cctv_att_both_gap_minutes = _f('both_gap_minutes', fields.Integer, 'Single-door toggle gap (min)')
    cctv_att_stale_open_hours = _f('stale_open_hours', fields.Integer, 'Forgotten check-out after (hours, 0 = off)')
    cctv_att_max_age_minutes = _f('max_age_minutes', fields.Integer, 'Late punch goes to review after (min)')
    cctv_att_snapshot_retention_days = _f('snapshot_retention_days', fields.Integer, 'Keep punch snapshots (days)')
    cctv_att_event_confirm_count = _f('event_confirm_count', fields.Integer, 'AI events needed')
    cctv_att_event_confirm_seconds = _f('event_confirm_seconds', fields.Integer, 'AI events must agree within (s)')
    cctv_att_require_consent = _f('require_consent', fields.Boolean, 'Require biometric consent')
    cctv_att_log_ignored = _f('log_ignored', fields.Boolean, 'Also log ignored sightings')
    cctv_att_alert_unknown = _f('alert_unknown', fields.Boolean, 'Alert on unknown faces')
    cctv_att_skip_employee_photo = _f('skip_employee_photo', fields.Boolean, 'Do not use the employee profile photo')
    cctv_att_disable_event_api = _f('disable_event_api', fields.Boolean, 'Ignore faces from the AI event API')
    cctv_att_readiness = fields.Text(string='Face attendance readiness', compute='_compute_cctv_att_readiness')

    def _compute_cctv_att_readiness(self):
        text = self.env['cctv.attendance.config'].readiness_text()
        for rec in self:
            rec.cctv_att_readiness = text

    def set_values(self):
        super().set_values()
        self.env['cctv.attendance.config'].bump_version()

    def action_cctv_att_enroll_all(self):
        employees = self.env['hr.employee'].sudo().search([])
        return employees.action_enroll_face()
