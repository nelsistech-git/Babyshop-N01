# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentCapacityPlan(models.Model):
    """Line/date-wise Capacity Planning. Formulas from SRS:
    Daily Capacity = Operators x Working Hours x Efficiency% (Production
    Management SRS s.10) and Daily Capacity = Available Minutes x
    Efficiency / SMV (Planning & MES SRS s.9, Shop Floor SRS s.13)."""
    _name = 'garment.capacity.plan'
    _description = 'Garment Capacity Plan'
    _order = 'date desc'

    plan_id = fields.Many2one('garment.production.plan', string='Production Plan', ondelete='cascade')
    line_id = fields.Many2one('garment.production.line', string='Production Line', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    operators = fields.Integer(string='Available Operators')
    working_hours = fields.Float(string='Working Hours', default=8.0)
    efficiency_pct = fields.Float(string='Efficiency (%)', default=70.0)
    smv = fields.Float(string='SMV (Minutes)', digits=(6, 3))

    daily_capacity = fields.Float(string='Daily Capacity (PCS)', compute='_compute_capacity', store=True)
    allocated_qty = fields.Float(string='Allocated Quantity (PCS)')
    available_capacity = fields.Float(string='Remaining Capacity (PCS)', compute='_compute_capacity', store=True)

    @api.depends('operators', 'working_hours', 'efficiency_pct', 'smv', 'allocated_qty')
    def _compute_capacity(self):
        for rec in self:
            if rec.smv:
                available_minutes = rec.operators * rec.working_hours * 60
                rec.daily_capacity = (available_minutes * (rec.efficiency_pct / 100.0)) / rec.smv if rec.smv else 0.0
            else:
                rec.daily_capacity = rec.operators * rec.working_hours * (rec.efficiency_pct / 100.0) * 60
            rec.available_capacity = rec.daily_capacity - rec.allocated_qty
