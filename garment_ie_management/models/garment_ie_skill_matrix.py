# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Skill Matrix Management (SRS s.17-19, s.54) — per-employee, per-operation
skill level, efficiency % and training status, used for Skill-Based Operator
Allocation recommendation and as an input to Line Balancing.

Note: ``garment_hr`` already ships a general HR competency record
(``garment.hr.skill.matrix``, generic department-level operation categories +
1-5 proficiency). This IE model is deliberately finer-grained — it is scoped
to actual IE Operation Master records with an efficiency % used directly in
Line Balancing capacity math, which the HR record does not carry.
"""
from odoo import api, fields, models


class GarmentIeSkillMatrix(models.Model):
    _name = 'garment.ie.skill.matrix'
    _description = 'Garment IE Operator Skill Matrix'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'employee_id'
    _rec_name = 'name'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, tracking=True)
    name = fields.Char(string='Name', compute='_compute_name', store=True)
    line_ids = fields.One2many('garment.ie.skill.matrix.line', 'matrix_id', string='Operation Skills')
    skill_count = fields.Integer(string='Operations Skilled', compute='_compute_counts', store=True)
    expert_count = fields.Integer(string='Expert Operations', compute='_compute_counts', store=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('employee_uniq', 'unique(employee_id, company_id)',
         'An operator can only have one skill matrix profile!'),
    ]

    @api.depends('employee_id', 'employee_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.employee_id.name or ''

    @api.depends('line_ids.skill_level')
    def _compute_counts(self):
        for rec in self:
            rec.skill_count = len(rec.line_ids)
            rec.expert_count = len(rec.line_ids.filtered(lambda l: l.skill_level == 'expert'))


class GarmentIeSkillMatrixLine(models.Model):
    """Operator Skill Profile line (SRS s.18): one operation with a skill
    level, efficiency % and training status."""
    _name = 'garment.ie.skill.matrix.line'
    _description = 'Garment IE Operator Skill Matrix Line'
    _order = 'matrix_id, operation_id'

    matrix_id = fields.Many2one('garment.ie.skill.matrix', string='Skill Matrix', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='matrix_id.employee_id', string='Employee', store=True, readonly=True)
    operation_id = fields.Many2one('garment.ie.operation', string='Operation', required=True)
    skill_level = fields.Selection([
        ('beginner', 'Beginner - New Operator'),
        ('intermediate', 'Intermediate - Normal Skill'),
        ('expert', 'Expert - High Skill'),
    ], string='Skill Level', default='beginner', required=True)
    efficiency_pct = fields.Float(string='Efficiency (%)')
    training_status = fields.Selection([
        ('not_trained', 'Not Trained'), ('in_training', 'In Training'),
        ('trained', 'Trained'), ('certified', 'Certified'),
    ], string='Training Status', default='not_trained')
    certified_date = fields.Date(string='Certified Date')
    last_assessed_date = fields.Date(string='Last Assessed Date')

    _sql_constraints = [
        ('matrix_operation_uniq', 'unique(matrix_id, operation_id)',
         'This operator already has a skill entry for this operation!'),
    ]
