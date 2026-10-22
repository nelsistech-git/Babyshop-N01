# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
IE Improvement Tracking (SRS s.34, s.47-48) — continuous improvement
projects: Problem Identified -> IE Analysis -> Improvement Plan ->
Implementation -> Result Measurement -> Approval.
"""
from odoo import api, fields, models, _


class GarmentIeImprovement(models.Model):
    _name = 'garment.ie.improvement'
    _description = 'Garment IE Improvement Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'improvement_number'

    improvement_number = fields.Char(string='Reference', copy=False, readonly=True, default=lambda s: _('New'))
    title = fields.Char(string='Title', required=True, tracking=True)
    improvement_type = fields.Selection([
        ('method', 'Method Improvement'), ('layout', 'Layout Improvement'),
        ('machine', 'Machine Improvement'), ('skill', 'Skill Improvement'),
        ('automation', 'Automation Improvement'),
    ], string='Improvement Type', required=True, tracking=True)

    line_id = fields.Many2one('garment.production.line', string='Production Line')
    style_id = fields.Many2one('garment.style', string='Style')
    operation_id = fields.Many2one('garment.ie.operation', string='Operation')
    method_study_id = fields.Many2one('garment.ie.method.study', string='Related Method Study')
    motion_study_id = fields.Many2one('garment.ie.motion.study', string='Related Motion Study')
    line_balance_id = fields.Many2one('garment.ie.line.balance', string='Related Line Balancing Study')

    problem_description = fields.Text(string='Problem', required=True)
    root_cause = fields.Text(string='Root Cause')
    improvement_action = fields.Text(string='Improvement Action')
    expected_benefit = fields.Text(string='Expected Benefit')
    actual_result = fields.Text(string='Actual Result')

    output_before = fields.Float(string='Output Before (PCS/Day)')
    output_after = fields.Float(string='Output After (PCS/Day)')
    operators_before = fields.Integer(string='Operators Before')
    operators_after = fields.Integer(string='Operators After')
    improvement_pct = fields.Float(string='Improvement (%)', compute='_compute_improvement_pct', store=True)

    cost_saving_amount = fields.Monetary(string='Cost Saving', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    responsible_id = fields.Many2one('garment.hr.employee', string='Responsible IE Engineer')
    state = fields.Selection([
        ('identified', 'Problem Identified'), ('analysis', 'IE Analysis'),
        ('planned', 'Improvement Plan'), ('implemented', 'Implementation'),
        ('measured', 'Result Measurement'), ('approved', 'Approved'),
    ], string='Status', default='identified', tracking=True)
    target_date = fields.Date(string='Target Date')
    implemented_date = fields.Date(string='Implemented Date')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('output_before', 'output_after')
    def _compute_improvement_pct(self):
        for rec in self:
            rec.improvement_pct = ((rec.output_after - rec.output_before) / rec.output_before * 100.0
                                    if rec.output_before else 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('improvement_number', _('New')) == _('New'):
                vals['improvement_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.ie.improvement') or _('New')
        return super().create(vals_list)

    def action_start_analysis(self):
        self.write({'state': 'analysis'})

    def action_plan(self):
        self.write({'state': 'planned'})

    def action_implement(self):
        self.write({'state': 'implemented', 'implemented_date': fields.Date.context_today(self)})

    def action_measure(self):
        self.write({'state': 'measured'})

    def action_approve(self):
        self.write({'state': 'approved'})
