# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Employee Exit Management + Employee Clearance Management (Module 36 SRS
sections 50-51) — garment.hr.exit. Entirely missing from the original
build: Employee.status had 'resigned'/'terminated' options but no actual
Resignation -> Approval -> Clearance -> Final Settlement -> Archive
workflow behind them, and no Provident Fund/Gratuity settlement logic at
all despite the module's own summary promising "PF/gratuity accrual".

Gratuity formula used: gratuity_amount = (last_basic_salary / 30) x
gratuity_days_per_year x years_of_service. This mirrors the common
Bangladesh RMG practice of "30 days' wages per year of completed service"
under the Bangladesh Labour Act 2006 (as amended); gratuity_days_per_year
is left editable per record since exact entitlement varies by length of
service band and individual company policy — see IMPLEMENTATION_NOTES.md.
"""
from odoo import api, fields, models, _


class GarmentHrExit(models.Model):
    _name = 'garment.hr.exit'
    _description = 'Garment Employee Exit / Clearance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'notice_date desc'

    exit_number = fields.Char(string='Exit Number', copy=False, readonly=True, default=lambda s: _('New'))
    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    exit_type = fields.Selection([
        ('resignation', 'Resignation'), ('termination', 'Termination'),
    ], string='Exit Type', required=True, default='resignation')
    notice_date = fields.Date(string='Notice Date', default=fields.Date.context_today)
    last_working_date = fields.Date(string='Last Working Date')
    reason = fields.Text(string='Reason')

    # Clearance Management (SRS section 51: HR / Finance / Inventory / IT / Administration)
    hr_clearance = fields.Boolean(string='HR Clearance')
    finance_clearance = fields.Boolean(string='Finance Clearance')
    inventory_clearance = fields.Boolean(string='Inventory Clearance')
    it_clearance = fields.Boolean(string='IT Clearance')
    admin_clearance = fields.Boolean(string='Administration Clearance')
    all_clearance_done = fields.Boolean(string='All Clearances Done', compute='_compute_all_clearance', store=True)

    # Final Settlement
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    last_basic_salary = fields.Monetary(string='Last Basic Salary', currency_field='currency_id')
    years_of_service = fields.Float(string='Years of Service', compute='_compute_years_of_service', store=True)
    gratuity_days_per_year = fields.Integer(string='Gratuity Days / Year of Service', default=30)
    gratuity_amount = fields.Monetary(string='Gratuity Amount', compute='_compute_settlement', store=True,
                                       currency_field='currency_id')
    outstanding_dues = fields.Monetary(string='Outstanding Salary/Dues', currency_field='currency_id')
    loan_deduction = fields.Monetary(string='Outstanding Loan Deduction', currency_field='currency_id')
    final_settlement_amount = fields.Monetary(string='Final Settlement Amount', compute='_compute_settlement',
                                               store=True, currency_field='currency_id')

    status = fields.Selection([
        ('draft', 'Draft'), ('notice', 'Notice Period'), ('clearance', 'Clearance In Progress'),
        ('settled', 'Settled'), ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('hr_clearance', 'finance_clearance', 'inventory_clearance', 'it_clearance', 'admin_clearance')
    def _compute_all_clearance(self):
        for rec in self:
            rec.all_clearance_done = all([
                rec.hr_clearance, rec.finance_clearance, rec.inventory_clearance,
                rec.it_clearance, rec.admin_clearance,
            ])

    @api.depends('employee_id.joining_date', 'last_working_date')
    def _compute_years_of_service(self):
        for rec in self:
            start = rec.employee_id.joining_date
            end = rec.last_working_date
            if start and end and end > start:
                rec.years_of_service = round((end - start).days / 365.0, 2)
            else:
                rec.years_of_service = 0.0

    @api.depends('last_basic_salary', 'gratuity_days_per_year', 'years_of_service',
                 'outstanding_dues', 'loan_deduction')
    def _compute_settlement(self):
        for rec in self:
            daily_wage = (rec.last_basic_salary or 0.0) / 30.0
            rec.gratuity_amount = round(daily_wage * (rec.gratuity_days_per_year or 0) * (rec.years_of_service or 0.0), 2)
            rec.final_settlement_amount = (rec.gratuity_amount + rec.outstanding_dues) - rec.loan_deduction

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('exit_number', _('New')) == _('New'):
                vals['exit_number'] = self.env['ir.sequence'].next_by_code('garment.hr.exit') or _('New')
        return super().create(vals_list)

    def action_start_notice(self):
        self.write({'status': 'notice'})

    def action_start_clearance(self):
        self.write({'status': 'clearance'})

    def action_settle(self):
        self.write({'status': 'settled'})

    def action_archive_employee(self):
        for rec in self:
            rec.employee_id.write({
                'status': 'terminated' if rec.exit_type == 'termination' else 'resigned',
                'active': False,
            })
            rec.status = 'archived'
