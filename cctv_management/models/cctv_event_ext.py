# -*- coding: utf-8 -*-
"""v4.5 event extensions: Google Drive hand-off and human review (feeds AI training)."""
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)
_RANK = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
_PPE_BEHAVIORS = {'no_helmet', 'no_vest', 'no_mask', 'no_uniform', 'no_helmet_compliance', 'no_mask_compliance'}


class CctvEventDrive(models.Model):
    _inherit = 'cctv.event'

    review_state = fields.Selection([
        ('pending', 'Not reviewed'), ('confirmed', 'Correct detection'), ('false_positive', 'False alarm')],
        default='pending', index=True, copy=False, string='Review',
        help='Mark real detections and false alarms; they become labelled training samples for the AI models.')
    reviewed_by = fields.Many2one('res.users', copy=False, readonly=True)
    reviewed_on = fields.Datetime(copy=False, readonly=True)
    drive_upload_ids = fields.One2many('cctv.drive.upload', 'event_id', string='Drive Files')
    drive_snapshot_link = fields.Char(compute='_compute_drive_links')
    drive_clip_link = fields.Char(compute='_compute_drive_links')

    @api.depends('drive_upload_ids.state', 'drive_upload_ids.web_link')
    def _compute_drive_links(self):
        for rec in self:
            done = rec.sudo().drive_upload_ids.filtered(lambda u: u.state == 'done' and u.web_link)
            snap = done.filtered(lambda u: u.kind == 'snapshot')[:1]
            clip = done.filtered(lambda u: u.kind == 'clip')[:1]
            rec.drive_snapshot_link = snap.web_link or False
            rec.drive_clip_link = clip.web_link or False

    # ---------------------------------------------------------------- severity / model kind
    def _severity(self):
        self.ensure_one()
        if self.detection_type in self._FIRE_SMOKE or self.behavior_type in self._INCIDENT_BEHAVIORS:
            return 'critical'
        if self.behavior_type in self._LOW_SEVERITY_BEHAVIORS:
            return 'low'
        if self.behavior_type in self._MEDIUM_SEVERITY_BEHAVIORS:
            return 'medium'
        return 'high'

    def _severity_rank(self):
        return _RANK[self._severity()]

    @api.model
    def _severity_rank_of(self, name):
        return _RANK.get(name, 2)

    def _drive_worthy(self):
        """Only things somebody may want evidence for - never the constant 'person walking' frames."""
        self.ensure_one()
        return bool(self.detection_type in ('fire', 'smoke', 'tamper')
                    or (self.behavior_type and self.behavior_type != 'none')
                    or self.alert_id)

    def _ai_model_kind(self):
        self.ensure_one()
        if self.detection_type in ('fire', 'smoke'):
            return 'fire_smoke'
        if self.behavior_type in _PPE_BEHAVIORS:
            return 'ppe'
        if self.behavior_type in ('forklift_movement', 'package_removal', 'door_open'):
            return 'warehouse'
        return 'general'

    # ---------------------------------------------------------------- create hook
    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        Upload = self.env['cctv.drive.upload']
        for event in events:
            try:
                with self.env.cr.savepoint():
                    Upload.enqueue_for_event(event)
            except Exception:                         # Drive must never block event intake
                _logger.exception('could not queue event %s for Google Drive', event.id)
        return events

    # ---------------------------------------------------------------- review (AI training feedback)
    def _set_review(self, state):
        self.write({'review_state': state, 'reviewed_by': self.env.user.id,
                    'reviewed_on': fields.Datetime.now()})
        drive_on = self.env['cctv.gdrive'].is_connected() and \
            self.env['ir.config_parameter'].sudo().get_param('cctv_management.drive_training_export', 'True') == 'True'
        if drive_on:
            for ev in self:
                self.env['cctv.drive.upload'].enqueue_training(ev, state)

    def action_review_confirm(self):
        self._set_review('confirmed')
        return True

    def action_review_false_positive(self):
        self._set_review('false_positive')
        return True
