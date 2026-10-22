# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Performance Management + Performance Evaluation (SRS sections 46-47) —
garment.hr.performance. Both SRS documents list six identical Evaluation
Areas (Productivity, Quality, Attendance, Discipline, Skill, Teamwork) —
the original build only scored four of them, missing Skill and Teamwork
entirely. The five-band Rating Scale (SRS section 43: Excellent 90-100 /
Very Good 80-89 / Good 70-79 / Average 60-69 / Need Improvement <60) is
now matched exactly (existing selection keys are kept unchanged so
previously stored ratings keep resolving — only the labels/thresholds
were wrong).

Full role-specific KPI Management (SRS section 42: separate Worker /
Supervisor / Manager KPI sets such as Line Efficiency, Cost Control,
Delivery Performance) is deliberately not modelled as extra dynamic
fields here — see IMPLEMENTATION_NOTES.md for why and what already
covers it (garment_ie_management's line-balance/OEE/productivity models).
"""
from odoo import fields, models


class GarmentHrPerformance(models.Model):
    _name = 'garment.hr.performance'
    _description = 'Garment Employee Performance Review'
    _inherit = ['mail.thread']
    _order = 'review_date desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    review_period_start = fields.Date(string='Review Period Start')
    review_period_end = fields.Date(string='Review Period End')
    review_date = fields.Date(string='Review Date', default=fields.Date.context_today)
    reviewer_id = fields.Many2one('res.users', string='Reviewer', default=lambda s: s.env.user)

    productivity_score = fields.Float(string='Productivity Score (%)')
    quality_score = fields.Float(string='Quality Score (%)')
    attendance_score = fields.Float(string='Attendance Score (%)')
    discipline_score = fields.Float(string='Discipline Score (%)')
    skill_score = fields.Float(string='Skill Score (%)')
    teamwork_score = fields.Float(string='Teamwork Score (%)')
    overall_score = fields.Float(string='Overall Score (%)', compute='_compute_overall_score', store=True)
    rating = fields.Selection([
        ('outstanding', 'Excellent'), ('good', 'Very Good'), ('average', 'Good'),
        ('below_average', 'Average'), ('poor', 'Need Improvement'),
    ], string='Rating', compute='_compute_overall_score', store=True)
    comments = fields.Text(string='Comments')
    status = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('acknowledged', 'Employee Acknowledged'),
    ], string='Status', default='draft', tracking=True)

    def _compute_overall_score(self):
        for rec in self:
            scores = [rec.productivity_score, rec.quality_score, rec.attendance_score,
                      rec.discipline_score, rec.skill_score, rec.teamwork_score]
            valid = [s for s in scores if s]
            score = sum(valid) / len(valid) if valid else 0.0
            rec.overall_score = score
            # SRS section 43 Rating Scale: Excellent 90-100 / Very Good 80-89 /
            # Good 70-79 / Average 60-69 / Need Improvement below 60.
            if score >= 90:
                rec.rating = 'outstanding'
            elif score >= 80:
                rec.rating = 'good'
            elif score >= 70:
                rec.rating = 'average'
            elif score >= 60:
                rec.rating = 'below_average'
            else:
                rec.rating = 'poor'
