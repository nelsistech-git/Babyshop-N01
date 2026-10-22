# -*- coding: utf-8 -*-
from odoo import models, fields


class CctvRecordingSchedule(models.Model):
    _name = 'cctv.recording.schedule'
    _description = 'CCTV Recording Schedule'

    name = fields.Char(required=True)
    monday = fields.Boolean(default=True)
    tuesday = fields.Boolean(default=True)
    wednesday = fields.Boolean(default=True)
    thursday = fields.Boolean(default=True)
    friday = fields.Boolean(default=True)
    saturday = fields.Boolean(default=True)
    sunday = fields.Boolean(default=True)
    start_time = fields.Float(default=0.0, help='24h float, e.g. 18.5 = 18:30')
    end_time = fields.Float(default=23.99)
    camera_ids = fields.One2many('cctv.camera', 'recording_schedule_id', string='Cameras')
