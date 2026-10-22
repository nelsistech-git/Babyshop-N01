# -*- coding: utf-8 -*-
"""Biometric data controls for face recognition (SRS feature 7): consent, retention, erasure."""
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CctvPersonBiometric(models.Model):
    _inherit = 'cctv.person'

    vehicle_ids = fields.One2many('cctv.person.vehicle', 'person_id', string='Registered Vehicles')
    biometric_consent = fields.Boolean(
        string='Biometric Consent Recorded',
        help='Tick when the person has been informed and agreed to face recognition (where the law requires it).')
    biometric_consent_date = fields.Date()
    biometric_retention_until = fields.Date(
        string='Keep Biometrics Until',
        help='After this date the photo and face-embedding reference are erased automatically. '
             'Empty = keep until manually erased (not recommended for visitors).')
    biometric_purged = fields.Boolean(readonly=True)

    def action_purge_biometrics(self):
        """Right-to-erasure: wipe photo + embedding reference + stored face snapshots."""
        for rec in self:
            self.env['cctv.face.log'].sudo().search([('person_id', '=', rec.id)]).unlink()
            self.env['cctv.event'].sudo().search(
                [('person_id', '=', rec.id), ('detection_type', '=', 'face')]).write({'snapshot': False})
            rec.write({'photo': False, 'face_embedding_ref': False, 'biometric_purged': True})
            rec.message_post(body='Biometric data erased by %s. Also delete this person\'s folder from the '
                                  'AI service face gallery (cctv_ai_service/face_gallery).' % self.env.user.name)

    @api.model
    def cron_purge_biometric_data(self):
        """Daily: enforce retention limits on face logs, face snapshots and expired people."""
        params = self.env['ir.config_parameter'].sudo()
        days = int(params.get_param('cctv_management.face_log_retention_days', '30') or 30)
        cutoff = fields.Datetime.now() - timedelta(days=days)

        logs = self.env['cctv.face.log'].sudo().search([('create_date', '<', cutoff)])
        n_logs = len(logs)
        logs.unlink()
        events = self.env['cctv.event'].sudo().search(
            [('detection_type', '=', 'face'), ('event_time', '<', cutoff), ('snapshot', '!=', False)])
        n_snap = len(events)
        events.write({'snapshot': False})

        expired = self.sudo().search([('biometric_retention_until', '!=', False),
                                      ('biometric_retention_until', '<', fields.Date.today()),
                                      ('biometric_purged', '=', False)])
        expired.action_purge_biometrics()
        _logger.info('CCTV biometric retention: %s face logs, %s face snapshots, %s people erased',
                     n_logs, n_snap, len(expired))
