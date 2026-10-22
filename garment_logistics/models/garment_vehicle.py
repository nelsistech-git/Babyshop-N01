# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentVehicle(models.Model):
    """Vehicle Management (SRS section 23) — garment.vehicle."""
    _name = 'garment.vehicle'
    _description = 'Garment Transport Vehicle'
    _order = 'vehicle_number'

    vehicle_number = fields.Char(string='Vehicle Number', required=True)
    vehicle_type = fields.Selection([
        ('truck', 'Truck'), ('covered_van', 'Covered Van'),
        ('container_carrier', 'Container Carrier'), ('pickup', 'Pickup'),
    ], string='Type', required=True)
    capacity = fields.Char(string='Capacity')
    driver_id = fields.Many2one('garment.driver', string='Assigned Driver')
    owner = fields.Selection([('company', 'Company Owned'), ('hired', 'Hired')], string='Owner', default='hired')
    insurance_expiry = fields.Date(string='Insurance Expiry')
    fitness_cert_expiry = fields.Date(string='Fitness Certificate Expiry')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('vehicle_number_uniq', 'unique(vehicle_number)', 'Vehicle Number must be unique!'),
    ]
