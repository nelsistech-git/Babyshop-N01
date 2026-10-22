# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentOperatorPerformance(models.Model):
    """Operator Performance scorecard (daily). See Advanced MES SRS s.21-27
    (Operator Performance Management, Performance Score, Incentive
    Integration), Planning & MES SRS s.27, Shop Floor SRS s.22."""
    _name = 'garment.operator.performance'
    _description = 'Garment Operator Performance'
    _order = 'date desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True)
    operation_name = fields.Char(string='Operation')
    line_id = fields.Many2one('garment.production.line', string='Production Line')
    production_order_id = fields.Many2one('garment.production.order', string='Production Order')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)

    target_qty = fields.Float(string='Target Quantity (PCS)')
    actual_qty = fields.Float(string='Actual Quantity (PCS)')
    efficiency_pct = fields.Float(string='Efficiency (%)', compute='_compute_efficiency', store=True)
    quality_score = fields.Float(string='Quality Score (%)', default=100.0)
    attendance_score = fields.Float(string='Attendance Score (%)', default=100.0)

    # Performance Score = Efficiency + Quality Score + Attendance Score (weighted average, SRS s.26)
    performance_score = fields.Float(string='Performance Score (%)', compute='_compute_efficiency', store=True)
    incentive_amount = fields.Monetary(string='Incentive Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    skill_level = fields.Selection([
        ('beginner', 'Beginner'), ('intermediate', 'Intermediate'),
        ('skilled', 'Skilled'), ('expert', 'Expert'), ('trainer', 'Trainer'),
    ], string='Skill Level', related='employee_id.skill_level', store=True, readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('target_qty', 'actual_qty', 'quality_score', 'attendance_score')
    def _compute_efficiency(self):
        for rec in self:
            rec.efficiency_pct = (rec.actual_qty / rec.target_qty * 100.0) if rec.target_qty else 0.0
            rec.performance_score = (rec.efficiency_pct + rec.quality_score + rec.attendance_score) / 3.0
