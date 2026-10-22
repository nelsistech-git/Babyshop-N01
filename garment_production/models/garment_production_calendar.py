# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentProductionCalendar(models.Model):
    """Factory production calendar: working days, holidays, shift timing,
    maintenance windows. See Production Management SRS s.20, Planning & MES
    SRS s.10."""
    _name = 'garment.production.calendar'
    _description = 'Garment Production Calendar'
    _order = 'date desc'

    name = fields.Char(string='Title', compute='_compute_name', store=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    line_id = fields.Many2one('garment.production.line', string='Production Line')
    shift = fields.Selection([
        ('morning', 'Morning'), ('evening', 'Evening'), ('night', 'Night'), ('general', 'General'),
    ], string='Shift', default='general')
    day_type = fields.Selection([
        ('working', 'Working Day'), ('holiday', 'Holiday'), ('weekly_off', 'Weekly Off'),
    ], string='Day Type', default='working')
    production_status = fields.Selection([
        ('active', 'Active'), ('planned', 'Planned'), ('idle', 'Idle'),
    ], string='Production Status', default='planned')
    is_maintenance_window = fields.Boolean(string='Maintenance Scheduled')
    production_order_id = fields.Many2one('garment.production.order', string='Production Order')
    capacity_load_pct = fields.Float(string='Capacity Load (%)')
    notes = fields.Char(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s' % (rec.date or '', dict(rec._fields['shift'].selection).get(rec.shift, ''))
