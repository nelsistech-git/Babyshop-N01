# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Productivity Measurement / Operator Efficiency Report / SMV Variance Report
(SRS s.32-33, s.45-46) — Target vs. Actual output per employee/operation and
the standard garment-industry Efficiency % formula:

    Efficiency % = (Standard SMV x Actual Output) / Total Minutes Worked x 100

Distinct from ``garment_production``'s ``garment.operator.performance``
(a quality/attendance/incentive scorecard using a simple Actual/Target
ratio) — this record is the IE-side SMV-standard-vs-actual analysis feeding
the SMV Variance Report.
"""
from odoo import api, fields, models


class GarmentIeProductivityRecord(models.Model):
    _name = 'garment.ie.productivity.record'
    _description = 'Garment IE Productivity Record'
    _order = 'date desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True)
    operation_id = fields.Many2one('garment.ie.operation', string='Operation')
    line_id = fields.Many2one('garment.production.line', string='Production Line')
    production_order_id = fields.Many2one('garment.production.order', string='Production Order')
    work_order_id = fields.Many2one('garment.work.order', string='Work Order')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)

    target_output = fields.Float(string='Target Output (PCS)')
    actual_output = fields.Float(string='Actual Output (PCS)')
    productivity_pct = fields.Float(string='Productivity (%)', compute='_compute_productivity', store=True,
                                     help='Productivity % = Actual Output / Target Output x 100')

    standard_smv = fields.Float(string='Standard SMV (Min)', digits=(6, 3))
    worked_minutes = fields.Float(string='Worked Minutes')
    actual_time_per_pc = fields.Float(string='Actual Time / PC (Min)', digits=(6, 3),
                                       compute='_compute_productivity', store=True)
    smv_variance = fields.Float(string='SMV Variance (Min)', digits=(6, 3), compute='_compute_productivity',
                                 store=True, help='Actual Time / PC - Standard SMV')
    efficiency_pct = fields.Float(string='Efficiency (%)', compute='_compute_productivity', store=True,
                                   help='Efficiency % = (Standard SMV x Actual Output) / Worked Minutes x 100')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('target_output', 'actual_output', 'worked_minutes', 'standard_smv')
    def _compute_productivity(self):
        for rec in self:
            rec.productivity_pct = (rec.actual_output / rec.target_output * 100.0
                                     if rec.target_output else 0.0)
            rec.actual_time_per_pc = (rec.worked_minutes / rec.actual_output
                                       if rec.actual_output else 0.0)
            rec.smv_variance = rec.actual_time_per_pc - rec.standard_smv
            rec.efficiency_pct = ((rec.standard_smv * rec.actual_output) / rec.worked_minutes * 100.0
                                   if rec.worked_minutes else 0.0)
