# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Employee Grade Management (HRM SRS section 12) + Salary Structure
Management (SRS section 34; Module 36 SRS section 32) + the "Minimum Wage
Structure" part of Bangladesh Garment Payroll Rules (Module 36 SRS section
33) — garment.hr.salary.structure. This is the Wage-Board grade table that
was entirely missing: Designation only carried a free-text 'grade' label
with no actual basic/HRA/medical/food/transport figures behind it, so
Payroll had nothing authoritative to calculate from.
"""
from odoo import api, fields, models


class GarmentHrSalaryStructure(models.Model):
    _name = 'garment.hr.salary.structure'
    _description = 'Garment HR Salary Structure (Wage-Board Grade)'
    _order = 'sequence, name'

    name = fields.Char(string='Grade Name', required=True, help='e.g. "Worker Grade-3" / "Operator Grade-A"')
    grade_code = fields.Char(string='Grade Code')
    sequence = fields.Integer(default=10)
    employee_category = fields.Selection([
        ('worker', 'Worker'), ('supervisor', 'Supervisor'), ('staff', 'Staff'), ('officer', 'Officer'),
        ('management', 'Management'), ('executive', 'Executive'), ('contract', 'Contract Employee'),
    ], string='Employee Category')
    is_wage_board_grade = fields.Boolean(
        string='Government Wage-Board Grade',
        help='Marks this as an official Bangladesh RMG Minimum Wage Board grade (Grade 1-7) '
             'rather than a company-defined structure.')

    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    basic_salary = fields.Monetary(string='Basic Salary', currency_field='currency_id', required=True)
    house_rent = fields.Monetary(string='House Rent Allowance', currency_field='currency_id')
    medical_allowance = fields.Monetary(string='Medical Allowance', currency_field='currency_id')
    food_allowance = fields.Monetary(string='Food Allowance', currency_field='currency_id')
    transport_allowance = fields.Monetary(string='Transport/Conveyance Allowance', currency_field='currency_id')
    gross_salary = fields.Monetary(string='Gross Salary', compute='_compute_gross_salary', store=True,
                                    currency_field='currency_id')

    effective_date = fields.Date(string='Effective Date', default=fields.Date.context_today)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('basic_salary', 'house_rent', 'medical_allowance', 'food_allowance', 'transport_allowance')
    def _compute_gross_salary(self):
        for rec in self:
            rec.gross_salary = (rec.basic_salary + rec.house_rent + rec.medical_allowance
                                 + rec.food_allowance + rec.transport_allowance)
