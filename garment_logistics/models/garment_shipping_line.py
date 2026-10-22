# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentShippingLine(models.Model):
    """Shipping Line Management (SRS section 14) — garment.shipping.line."""
    _name = 'garment.shipping.line'
    _description = 'Garment Shipping Line'
    _order = 'name'

    name = fields.Char(string='Shipping Line Name', required=True)
    contact = fields.Char(string='Contact')
    vessel_service = fields.Char(string='Vessel Service')
    origin_port = fields.Char(string='Origin Port')
    destination_port = fields.Char(string='Destination Port')
    route = fields.Char(string='Route', compute='_compute_route', store=True)
    transit_time_days = fields.Integer(string='Transit Time (days)')
    active = fields.Boolean(default=True)

    @api.depends('origin_port', 'destination_port')
    def _compute_route(self):
        for rec in self:
            rec.route = '%s -> %s' % (rec.origin_port or '?', rec.destination_port or '?')
