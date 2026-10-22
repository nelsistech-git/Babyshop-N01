# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentHrDesignation(models.Model):
    """Designation Management (SRS section 10) — garment.hr.designation."""
    _name = 'garment.hr.designation'
    _description = 'Garment HR Designation'
    _order = 'grade, name'

    name = fields.Char(required=True)
    grade = fields.Char(string='Grade')
    employee_category = fields.Selection([
        ('worker', 'Worker'), ('supervisor', 'Supervisor'), ('staff', 'Staff'), ('officer', 'Officer'),
        ('management', 'Management'), ('executive', 'Executive'), ('contract', 'Contract Employee'),
    ], string='Employee Category')
    is_piece_rate_eligible = fields.Boolean(string='Piece-Rate Eligible')
    salary_structure_id = fields.Many2one('garment.hr.salary.structure', string='Salary Structure (Wage-Board Grade)',
                                           help='The Basic/HRA/Medical/Food/Transport structure Payroll should '
                                                'calculate this designation\'s salary from.')
    responsibilities = fields.Text(string='Responsibilities')
    active = fields.Boolean(default=True)
