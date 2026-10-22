# -*- coding: utf-8 -*-
from odoo import models, fields


class CctvFaceLog(models.Model):
    _name = 'cctv.face.log'
    _description = 'Face Recognition Match Log'
    _order = 'detected_at desc'

    camera_id = fields.Many2one('cctv.camera', required=True)
    office_id = fields.Many2one(related='camera_id.office_id', store=True)
    person_id = fields.Many2one('cctv.person', string='Matched Person')
    is_unknown = fields.Boolean(string='Unknown Face')
    match_confidence = fields.Float(string='Match Confidence (%)')
    detected_at = fields.Datetime(default=fields.Datetime.now)
    snapshot = fields.Binary(attachment=True)
    linked_to_attendance = fields.Boolean(
        help='Set true if this match was used to auto check-in/out the employee in HR Attendance')
