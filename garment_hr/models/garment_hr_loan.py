# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Employee Loan Management (HRM SRS section 51) + Employee Advance
Management (Module 36 SRS section 37) — garment.hr.loan. The original
build only had bare advance_deduction/loan_recovery/advance_balance
amount fields sitting directly on the payslip with no request/approval
workflow behind them — this model adds the actual
Request -> HR Approval -> Finance Approval -> Disbursement -> Monthly
Recovery workflow the SRS describes.
"""
from odoo import api, fields, models, _


class GarmentHrLoan(models.Model):
    _name = 'garment.hr.loan'
    _description = 'Garment Employee Loan / Advance'
    _inherit = ['mail.thread']
    _order = 'request_date desc'

    loan_number = fields.Char(string='Loan Number', copy=False, readonly=True, default=lambda s: _('New'))
    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    loan_type = fields.Selection([
        ('salary_advance', 'Salary Advance'), ('emergency', 'Emergency Loan'),
        ('festival', 'Festival Loan'), ('personal', 'Personal Loan'),
    ], string='Loan Type', required=True, default='salary_advance')

    request_date = fields.Date(string='Request Date', default=fields.Date.context_today)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    amount = fields.Monetary(string='Loan Amount', currency_field='currency_id', required=True)
    monthly_recovery_amount = fields.Monetary(string='Monthly Recovery', currency_field='currency_id', required=True)
    outstanding_balance = fields.Monetary(string='Outstanding Balance', currency_field='currency_id',
                                           readonly=True, copy=False)

    reason = fields.Text(string='Reason')
    hr_approved_by_id = fields.Many2one('res.users', string='HR Approved By', readonly=True)
    finance_approved_by_id = fields.Many2one('res.users', string='Finance Approved By', readonly=True)
    disbursement_date = fields.Date(string='Disbursement Date', readonly=True)

    status = fields.Selection([
        ('draft', 'Requested'), ('hr_approved', 'HR Approved'), ('finance_approved', 'Finance Approved'),
        ('disbursed', 'Disbursed'), ('closed', 'Closed'), ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('loan_number', _('New')) == _('New'):
                vals['loan_number'] = self.env['ir.sequence'].next_by_code('garment.hr.loan') or _('New')
        return super().create(vals_list)

    def action_hr_approve(self):
        self.write({'status': 'hr_approved', 'hr_approved_by_id': self.env.user.id})

    def action_finance_approve(self):
        self.write({'status': 'finance_approved', 'finance_approved_by_id': self.env.user.id})

    def action_reject(self):
        self.write({'status': 'rejected'})

    def action_disburse(self):
        for rec in self:
            rec.write({
                'status': 'disbursed',
                'disbursement_date': fields.Date.context_today(rec),
                'outstanding_balance': rec.amount,
            })

    def action_record_monthly_recovery(self):
        """Deduct one month's recovery installment (mirrors what Payroll's
        loan_recovery deduction should book each period) and auto-close
        once fully recovered."""
        for rec in self:
            if rec.status != 'disbursed':
                continue
            new_balance = max(0.0, rec.outstanding_balance - rec.monthly_recovery_amount)
            vals = {'outstanding_balance': new_balance}
            if new_balance <= 0:
                vals['status'] = 'closed'
            rec.write(vals)
