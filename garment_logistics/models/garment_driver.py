# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentDriver(models.Model):
    """Driver Management (SRS section 24) — garment.driver."""
    _name = 'garment.driver'
    _description = 'Garment Driver'
    _order = 'name'

    name = fields.Char(string='Driver Name', required=True)
    mobile_number = fields.Char(string='Mobile Number')
    license_number = fields.Char(string='License Number')
    license_expiry = fields.Date(string='License Expiry')
    experience_years = fields.Integer(string='Experience (years)')
    assigned_vehicle_id = fields.Many2one('garment.vehicle', string='Assigned Vehicle')
    active = fields.Boolean(default=True)
