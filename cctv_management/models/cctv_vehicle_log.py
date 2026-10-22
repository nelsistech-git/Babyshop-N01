# -*- coding: utf-8 -*-
from odoo import models, fields


class CctvVehicleLog(models.Model):
    _name = 'cctv.vehicle.log'
    _description = 'Vehicle Entry/Exit Log (ANPR)'
    _order = 'entry_time desc'

    camera_id = fields.Many2one('cctv.camera', required=True)
    office_id = fields.Many2one(related='camera_id.office_id', store=True)
    vehicle_type = fields.Selection([
        ('car', 'Car'), ('truck', 'Truck'), ('bike', 'Bike'), ('bus', 'Bus'),
    ], required=True)
    license_plate = fields.Char(required=True, index=True)
    entry_time = fields.Datetime(default=fields.Datetime.now)
    exit_time = fields.Datetime()
    parking_minutes = fields.Float(compute='_compute_parking', store=True)
    speed_kph = fields.Float(string='Detected Speed (km/h)')
    is_authorized = fields.Boolean(default=True)
    snapshot = fields.Binary(attachment=True)

    def _compute_parking(self):
        for rec in self:
            if rec.entry_time and rec.exit_time:
                rec.parking_minutes = (rec.exit_time - rec.entry_time).total_seconds() / 60.0
            else:
                rec.parking_minutes = 0.0
