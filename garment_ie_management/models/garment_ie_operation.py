# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Operation Master library (SRS s.11) — a reusable catalog of standard garment
operations (Shoulder Join, Sleeve Attach, Collar Attach, ...) with a default
machine type, required skill and reference SMV. Style-specific routing lines
already live on ``garment.operation.routing.line`` (garment_production); this
master is the IE-side operation dictionary that the SMV Master, Time Study,
Skill Matrix and Line Balancing models are built on top of.
"""
from odoo import api, fields, models

MACHINE_TYPE_SELECTION = [
    ('single_needle', 'Single Needle'), ('overlock', 'Overlock'), ('flatlock', 'Flatlock'),
    ('bartack', 'Bartack'), ('buttonhole', 'Buttonhole'), ('button_attach', 'Button Attach'),
    ('manual', 'Manual'), ('other', 'Other'),
]

DEPARTMENT_SELECTION = [
    ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('washing', 'Washing'),
    ('finishing', 'Finishing'), ('packing', 'Packing'),
]

SKILL_LEVEL_SELECTION = [
    ('beginner', 'Beginner'), ('intermediate', 'Intermediate'),
    ('skilled', 'Skilled'), ('expert', 'Expert'), ('trainer', 'Trainer'),
]


class GarmentIeOperation(models.Model):
    _name = 'garment.ie.operation'
    _description = 'Garment IE Operation Master'
    _order = 'department, sequence, operation_code'
    _rec_name = 'name'

    operation_code = fields.Char(string='Operation Code', required=True, copy=False)
    name = fields.Char(string='Operation Name', required=True)
    department = fields.Selection(DEPARTMENT_SELECTION, string='Department', default='sewing', required=True)
    machine_type = fields.Selection(MACHINE_TYPE_SELECTION, string='Machine Type')
    skill_required = fields.Selection(SKILL_LEVEL_SELECTION, string='Skill Required', default='skilled')
    standard_smv = fields.Float(string='Reference SMV (Minutes)', digits=(6, 3),
                                 help='Default/reference SMV for this operation, used as a starting '
                                      'point for style-specific SMV Master entries.')
    sequence = fields.Integer(string='Sequence', default=10)
    operator_skill_count = fields.Integer(string='Skilled Operators', compute='_compute_operator_skill_count')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('operation_code_uniq', 'unique(operation_code, company_id)',
         'Operation Code must be unique per company!'),
    ]

    def _compute_operator_skill_count(self):
        SkillLine = self.env['garment.ie.skill.matrix.line']
        for rec in self:
            rec.operator_skill_count = SkillLine.search_count([('operation_id', '=', rec.id)])

    def action_view_recommended_operators(self):
        """Skill-Based Operator Allocation (SRS s.19): list operators with a
        recorded skill on this operation, best efficiency first."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'garment_ie_management.action_garment_ie_skill_matrix_line')
        action['domain'] = [('operation_id', '=', self.id)]
        action['context'] = {'default_operation_id': self.id}
        return action
