# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Bonus Management (Module 36 SRS section 38) — garment.hr.bonus. The
original build only had a single bonus_type/bonus_amount pair directly on
the payslip, which cannot represent that a worker may earn an Attendance
Bonus AND a Festival Bonus AND a Production Bonus in the same period. This
model tracks each bonus as its own auditable record which can optionally
be pulled into a payslip.
"""
from odoo import api, fields, models


class GarmentHrBonus(models.Model):
    _name = 'garment.hr.bonus'
    _description = 'Garment Employee Bonus'
    _inherit = ['mail.thread']
    _order = 'period desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    bonus_type = fields.Selection([
        ('festival', 'Festival Bonus'), ('performance', 'Performance Bonus'),
        ('attendance', 'Attendance Bonus'), ('production', 'Production Bonus'),
    ], string='Bonus Type', required=True)
    period = fields.Date(string='Period', default=fields.Date.context_today, required=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    note = fields.Text(string='Note')

    payroll_id = fields.Many2one('garment.hr.payroll', string='Included In Payslip',
                                  copy=False, ondelete='set null')
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    status = fields.Selection([
        ('draft', 'Draft'), ('approved', 'Approved'), ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def action_suggest_festival_amount(self):
        """Bangladesh RMG common practice: Festival Bonus = one month's Basic
        Salary, sourced from the employee's designation wage-board grade."""
        for rec in self:
            if rec.bonus_type != 'festival':
                continue
            structure = rec.employee_id.designation_id.salary_structure_id
            if structure:
                rec.amount = structure.basic_salary

    def action_approve(self):
        self.write({'status': 'approved', 'approved_by_id': self.env.user.id})

    def action_mark_paid(self):
        self.write({'status': 'paid'})
