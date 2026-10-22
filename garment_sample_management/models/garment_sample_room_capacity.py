# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentSampleRoomCapacity(models.Model):
    """Sample Room Capacity Planning (SRS section 28) — garment.sample.room.capacity.
    Tracks sample room resources (operators, sewing machines, cutting tables, finishing
    stations) and computes daily capacity = Available Hours × Operators × Efficiency."""
    _name = 'garment.sample.room.capacity'
    _description = 'Garment Sample Room Capacity Plan'
    _order = 'date desc, sample_room'

    name = fields.Char(string='Plan Reference', compute='_compute_name', store=True)
    sample_room = fields.Char(string='Sample Room', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    resource_type = fields.Selection([
        ('operator', 'Sample Operators'), ('sewing_machine', 'Sewing Machines'),
        ('cutting_table', 'Cutting Tables'), ('finishing_station', 'Finishing Stations'),
    ], string='Resource Type', required=True)
    resource_count = fields.Integer(string='Resource Count', default=1)
    available_hours = fields.Float(string='Available Hours/Day', default=8.0)
    efficiency = fields.Float(string='Efficiency (%)', default=100.0)
    daily_capacity = fields.Float(string='Daily Capacity (Hours)', compute='_compute_daily_capacity', store=True,
                                   help='Daily Capacity = Available Hours x Resource Count x Efficiency%.')
    active = fields.Boolean(default=True)

    @api.depends('sample_room', 'resource_type', 'date')
    def _compute_name(self):
        for rec in self:
            label = dict(rec._fields['resource_type'].selection).get(rec.resource_type, '')
            rec.name = '%s - %s (%s)' % (rec.sample_room or '', label, rec.date or '')

    @api.depends('available_hours', 'resource_count', 'efficiency')
    def _compute_daily_capacity(self):
        for rec in self:
            rec.daily_capacity = (rec.available_hours or 0.0) * (rec.resource_count or 0) * \
                ((rec.efficiency or 0.0) / 100.0)
