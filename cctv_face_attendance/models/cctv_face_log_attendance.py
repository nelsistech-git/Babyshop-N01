# -*- coding: utf-8 -*-
"""Lets the existing cctv_ai_service (InsightFace, /cctv/api/event) drive attendance too."""
import logging
from datetime import timedelta

from odoo import api, models

_logger = logging.getLogger(__name__)


class CctvFaceLogAttendance(models.Model):
    _inherit = 'cctv.face.log'

    @api.model_create_multi
    def create(self, vals_list):
        logs = super().create(vals_list)
        if self.env.context.get('skip_attendance_hook'):
            return logs
        cfg = self.env['cctv.attendance.config']
        if cfg.param('disable_event_api'):
            return logs
        for log in logs:
            try:
                if log.person_id and not log.is_unknown and log.camera_id.ai_attendance \
                        and log.person_id.person_type == 'employee':
                    with self.env.cr.savepoint():
                        log._attendance_from_event(cfg)
            except Exception:                      # never break the AI event intake
                _logger.exception('face attendance hook failed for face log %s', log.id)
        return logs

    def _attendance_from_event(self, cfg):
        """Several matching frames in a short window = one confirmed sighting."""
        self.ensure_one()
        window = cfg.param('event_confirm_seconds')
        needed = cfg.param('event_confirm_count')
        recent = self.sudo().search([
            ('person_id', '=', self.person_id.id), ('is_unknown', '=', False),
            ('camera_id.ai_attendance', '=', True),
            ('detected_at', '>=', self.detected_at - timedelta(seconds=window)),
            ('detected_at', '<=', self.detected_at)])
        if len(recent) < needed:
            return
        confidence = min(recent.mapped('match_confidence'))
        self.env['cctv.attendance.punch'].register_sighting(
            self.camera_id, self.person_id, confidence, when=self.detected_at, snapshot=self.snapshot,
            source='event_api', sightings=len(recent), face_log=self)
