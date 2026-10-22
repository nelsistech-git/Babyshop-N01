# -*- coding: utf-8 -*-
import re
from datetime import timedelta

from odoo import api, fields, models


def normalize_plate(plate):
    """Upper-case, letters+digits only, so 'dha-1234' == 'DHA 1234'."""
    return re.sub(r'[^A-Z0-9]', '', (plate or '').upper())


class CctvPersonVehicle(models.Model):
    """Registered vehicles of known people (employees, visitors, vendors, VIPs)."""
    _name = 'cctv.person.vehicle'
    _description = 'Registered Vehicle of a Person'

    person_id = fields.Many2one('cctv.person', required=True, ondelete='cascade')
    license_plate = fields.Char(required=True)
    plate_key = fields.Char(compute='_compute_plate_key', store=True, index=True)
    vehicle_type = fields.Selection([('car', 'Car'), ('truck', 'Truck'), ('bike', 'Bike'), ('bus', 'Bus')],
                                    default='car')
    notes = fields.Char()

    @api.depends('license_plate')
    def _compute_plate_key(self):
        for rec in self:
            rec.plate_key = normalize_plate(rec.license_plate)


class CctvVehicleLog(models.Model):
    _inherit = 'cctv.vehicle.log'

    plate_key = fields.Char(compute='_compute_plate_key', store=True, index=True)
    last_seen = fields.Datetime(default=fields.Datetime.now)
    person_id = fields.Many2one('cctv.person', string='Known Owner')
    visit_id = fields.Many2one('cctv.visit', string='Linked Visit')
    parking_minutes = fields.Float(compute='_compute_parking', store=True)

    @api.depends('license_plate')
    def _compute_plate_key(self):
        for rec in self:
            rec.plate_key = normalize_plate(rec.license_plate)

    @api.depends('entry_time', 'exit_time')
    def _compute_parking(self):   # original method lacked @api.depends, so it never refreshed
        for rec in self:
            if rec.entry_time and rec.exit_time:
                rec.parking_minutes = (rec.exit_time - rec.entry_time).total_seconds() / 60.0
            else:
                rec.parking_minutes = 0.0

    @api.model
    def register_plate(self, camera, plate, vehicle_type='car', speed_kph=0.0):
        """Entry/exit bookkeeping for one plate sighting. Returns the cctv.vehicle.log record.

        * gate 'entry'  : new open log (or just refresh last_seen if the same plate was seen < 10 min ago)
        * gate 'exit'   : closes the open log (and the linked visit) instead of creating a new one
        * gate 'both'   : sighting > 5 min after the last one toggles in/out
        Plates of registered people are linked to that person and to their open visit
        (auto-created for visitors), and a blacklisted owner raises an alert.
        """
        now = fields.Datetime.now()
        key = normalize_plate(plate)
        open_log = self.search([('plate_key', '=', key), ('exit_time', '=', False),
                                ('camera_id.office_id', '=', camera.office_id.id)], limit=1,
                               order='entry_time desc')
        role = camera.vehicle_direction or 'entry'

        if open_log:
            idle = now - (open_log.last_seen or open_log.entry_time)
            is_exit = role == 'exit' or (role == 'both' and idle > timedelta(minutes=5))
            if is_exit:
                open_log.write({'exit_time': now, 'last_seen': now})
                if open_log.visit_id and not open_log.visit_id.exit_time:
                    open_log.visit_id.write({'exit_time': now, 'exit_camera_id': camera.id})
                return open_log
            open_log.last_seen = now
            return open_log
        if role == 'exit':
            # exit gate saw a plate we never saw entering: log it as a closed record so nothing is lost
            return self.create({'camera_id': camera.id, 'vehicle_type': vehicle_type, 'license_plate': plate,
                                'speed_kph': speed_kph, 'entry_time': now, 'exit_time': now, 'last_seen': now})

        log = self.create({'camera_id': camera.id, 'vehicle_type': vehicle_type, 'license_plate': plate,
                           'speed_kph': speed_kph, 'entry_time': now, 'last_seen': now})
        log._link_owner_and_visit(camera)
        return log

    def _link_owner_and_visit(self, camera):
        self.ensure_one()
        reg = self.env['cctv.person.vehicle'].sudo().search([('plate_key', '=', self.plate_key)], limit=1)
        if not reg:
            return   # unregistered plate (customer, courier...): leave defaults, no owner
        person = reg.person_id
        vals = {'person_id': person.id, 'is_authorized': person.person_type != 'blacklisted'}
        Visit = self.env['cctv.visit'].sudo()
        visit = Visit.search([('person_id', '=', person.id), ('exit_time', '=', False),
                              ('office_id', '=', camera.office_id.id)], limit=1)
        if not visit and person.person_type in ('visitor', 'vendor', 'vip'):
            visit = Visit.create({'person_id': person.id, 'office_id': camera.office_id.id,
                                  'entry_camera_id': camera.id, 'entry_time': self.entry_time,
                                  'source': 'vehicle'})
        if visit:
            vals['visit_id'] = visit.id
        self.write(vals)
        if person.person_type == 'blacklisted':
            self.env['cctv.alert'].sudo().create({
                'name': "Blacklisted person's vehicle at %s: %s (%s)" % (camera.name, self.license_plate,
                                                                           person.name),
                'alert_type': 'intrusion', 'severity': 'critical', 'camera_id': camera.id,
                'office_id': camera.office_id.id,
            })
