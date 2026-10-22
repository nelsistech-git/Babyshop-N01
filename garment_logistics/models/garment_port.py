# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Port Management + Port Delivery Tracking (SRS sections 28-29) —
garment.port. Master data for export ports (Chittagong Port, Mongla
Port, Dhaka ICD, plus foreign discharge ports) referenced from
garment.container (loading/discharge port) and garment.transport.trip
(delivery destination port)."""
from odoo import fields, models


class GarmentPort(models.Model):
    _name = 'garment.port'
    _description = 'Garment Export/Import Port'
    _order = 'name'

    name = fields.Char(string='Port Name', required=True)
    port_type = fields.Selection([
        ('sea', 'Sea Port'), ('icd', 'Inland Container Depot'), ('air', 'Airport'),
    ], string='Port Type', default='sea', required=True)
    location = fields.Char(string='Location')
    country_id = fields.Many2one('res.country', string='Country')
    contact = fields.Char(string='Contact')
    operating_hours = fields.Char(string='Operating Hours')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('port_name_uniq', 'unique(name)', 'Port Name must be unique!'),
    ]
