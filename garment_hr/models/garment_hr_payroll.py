# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Payroll Management + Salary Structure + Bangladesh Garment Payroll Rules
+ Monthly Payroll Processing + Salary Slip Generation + Employee Advance
+ Bonus Management (SRS sections 31-38) — garment.hr.payroll. Kept as a
single monthly payslip model with earnings/deductions breakdown, since
that is how the SRS's own "Salary Slip Generation" example is structured.

Bangladesh RMG payroll rules implemented here:
- Wage-Board grade linkage: action_pull_salary_structure() pulls Basic/
  HRA/Medical/Food/Transport straight from the employee's designation's
  garment.hr.salary.structure (the Grade table), and is_below_minimum_wage
  flags a payslip whose Basic Salary undercuts that grade's wage-board
  minimum.
- Overtime at 2x hourly rate per the Bangladesh Labour Act 2006 (as
  amended) default (overtime_rate_multiplier default 2.0); OT hours can be
  pulled straight from attendance for the pay period instead of typed in.
- Festival Bonus / Attendance Bonus / Production Incentive are itemised
  earnings, each of which can be pulled in bulk from the corresponding
  garment.hr.bonus / garment.hr.incentive records for the period.
- Provident Fund: both the employee deduction (already present) and the
  employer's matching contribution are tracked (the employer share is
  informational — it is not part of Net Salary).
- Gratuity is accrued monthly here as an informational provision only;
  it is actually paid out at exit — see garment.hr.exit.
"""
from odoo import api, fields, models, _


class GarmentHrPayroll(models.Model):
    _name = 'garment.hr.payroll'
    _description = 'Garment Employee Payroll'
    _inherit = ['mail.thread']
    _order = 'period_end desc'

    payslip_number = fields.Char(string='Payslip Number', copy=False, readonly=True, default=lambda s: _('New'))
    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    salary_structure_id = fields.Many2one('garment.hr.salary.structure', string='Salary Structure (Wage-Board Grade)',
                                           help='Source structure used by "Pull From Salary Structure".')
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    # Earnings
    basic_salary = fields.Monetary(string='Basic Salary', currency_field='currency_id')
    house_rent = fields.Monetary(string='House Rent', currency_field='currency_id')
    medical_allowance = fields.Monetary(string='Medical Allowance', currency_field='currency_id')
    food_allowance = fields.Monetary(string='Food Allowance', currency_field='currency_id')
    transport_allowance = fields.Monetary(string='Transport Allowance', currency_field='currency_id')
    is_below_minimum_wage = fields.Boolean(string='Below Wage-Board Minimum', compute='_compute_totals', store=True,
                                            help='Basic Salary is lower than the linked Salary Structure grade\'s '
                                                 'Basic Salary — a Bangladesh Minimum Wage Board compliance flag.')

    overtime_hours = fields.Float(string='Overtime Hours')
    overtime_rate_multiplier = fields.Float(string='OT Rate Multiplier', default=2.0,
                                              help='Bangladesh garment rule default: 2x hourly rate.')
    hourly_rate = fields.Monetary(string='Hourly Rate', currency_field='currency_id')
    overtime_amount = fields.Monetary(string='Overtime Amount', compute='_compute_totals', store=True,
                                       currency_field='currency_id')

    attendance_bonus = fields.Monetary(string='Attendance Bonus', currency_field='currency_id')
    festival_bonus = fields.Monetary(string='Festival Bonus', currency_field='currency_id')
    production_incentive_amount = fields.Monetary(string='Production Incentive', currency_field='currency_id')

    bonus_type = fields.Selection([
        ('none', 'None'), ('festival', 'Festival Bonus'), ('attendance', 'Attendance Bonus'),
        ('production_incentive', 'Production Incentive'),
    ], string='Other Bonus Type', default='none')
    bonus_amount = fields.Monetary(string='Other Bonus/Incentive Amount', currency_field='currency_id')

    bonus_ids = fields.One2many('garment.hr.bonus', 'payroll_id', string='Itemised Bonuses')
    incentive_ids = fields.One2many('garment.hr.incentive', 'payroll_id', string='Itemised Incentives')

    gross_earnings = fields.Monetary(string='Gross Earnings', compute='_compute_totals', store=True,
                                      currency_field='currency_id')

    # Attendance summary (filled by "Pull From Attendance")
    worked_days = fields.Integer(string='Worked Days')
    absent_days = fields.Integer(string='Absent Days')
    late_minutes_total = fields.Integer(string='Total Late Minutes (period)')

    # Deductions
    late_deduction = fields.Monetary(string='Late Deduction', currency_field='currency_id')
    advance_deduction = fields.Monetary(string='Advance Salary Deduction', currency_field='currency_id')
    loan_recovery = fields.Monetary(string='Loan Recovery', currency_field='currency_id')
    tax_deduction = fields.Monetary(string='Tax Deduction', currency_field='currency_id')
    provident_fund_deduction = fields.Monetary(string='Provident Fund Deduction (Employee)', currency_field='currency_id')
    other_deduction = fields.Monetary(string='Other Deduction', currency_field='currency_id')
    total_deductions = fields.Monetary(string='Total Deductions', compute='_compute_totals', store=True,
                                        currency_field='currency_id')

    # Provident Fund (employer side) + Gratuity accrual — informational, not part of Net Salary
    provident_fund_employer_contribution = fields.Monetary(
        string='Provident Fund (Employer Contribution)', currency_field='currency_id',
        help='Employer-matched PF contribution for this period. Informational — not deducted from Net Salary.')
    gratuity_accrual = fields.Monetary(
        string='Gratuity Accrual (this period)', currency_field='currency_id', compute='_compute_totals',
        store=True, help='Monthly gratuity provision at 30 days\' Basic Salary per year of service, prorated to '
                          'one month (Basic / 30 x 30 / 12). Informational — actually paid out at exit, see '
                          'Employee Exit.')

    net_salary = fields.Monetary(string='Net Salary', compute='_compute_totals', store=True,
                                  currency_field='currency_id')

    # Advance tracking (SRS section 37)
    advance_requested = fields.Monetary(string='Advance Requested (this period)', currency_field='currency_id')
    advance_balance = fields.Monetary(string='Outstanding Advance Balance', currency_field='currency_id')

    bank_account_number = fields.Char(string='Bank Account Number')
    payment_status = fields.Selection([
        ('draft', 'Draft'), ('hr_verified', 'HR Verified'), ('approved', 'Payroll Approved'),
        ('processed', 'Processed'), ('bank_transfer_initiated', 'Bank Transfer Initiated'), ('paid', 'Paid'),
    ], string='Payment Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('basic_salary', 'house_rent', 'medical_allowance', 'food_allowance', 'transport_allowance',
                 'overtime_hours', 'overtime_rate_multiplier', 'hourly_rate', 'bonus_amount',
                 'attendance_bonus', 'festival_bonus', 'production_incentive_amount',
                 'late_deduction', 'advance_deduction', 'loan_recovery', 'tax_deduction',
                 'provident_fund_deduction', 'other_deduction', 'salary_structure_id')
    def _compute_totals(self):
        for rec in self:
            rec.overtime_amount = rec.overtime_hours * rec.hourly_rate * (rec.overtime_rate_multiplier or 2.0)
            rec.gross_earnings = (rec.basic_salary + rec.house_rent + rec.medical_allowance
                                   + rec.food_allowance + rec.transport_allowance
                                   + rec.overtime_amount + rec.bonus_amount
                                   + rec.attendance_bonus + rec.festival_bonus + rec.production_incentive_amount)
            rec.total_deductions = (rec.late_deduction + rec.advance_deduction + rec.loan_recovery
                                     + rec.tax_deduction + rec.provident_fund_deduction + rec.other_deduction)
            rec.net_salary = rec.gross_earnings - rec.total_deductions
            rec.gratuity_accrual = round((rec.basic_salary / 30.0) * 30.0 / 12.0, 2) if rec.basic_salary else 0.0

            structure = rec.salary_structure_id or rec.employee_id.designation_id.salary_structure_id
            rec.is_below_minimum_wage = bool(
                structure and rec.basic_salary and rec.basic_salary < structure.basic_salary)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('payslip_number', _('New')) == _('New'):
                vals['payslip_number'] = self.env['ir.sequence'].next_by_code('garment.hr.payroll') or _('New')
        return super().create(vals_list)

    def action_pull_salary_structure(self):
        """Bangladesh Garment Payroll Rules (SRS section 33): pull Basic/HRA/
        Medical/Food/Transport straight from the employee's wage-board grade."""
        for rec in self:
            structure = rec.employee_id.designation_id.salary_structure_id
            if not structure:
                continue
            rec.write({
                'salary_structure_id': structure.id,
                'basic_salary': structure.basic_salary,
                'house_rent': structure.house_rent,
                'medical_allowance': structure.medical_allowance,
                'food_allowance': structure.food_allowance,
                'transport_allowance': structure.transport_allowance,
            })

    def action_pull_attendance(self):
        """Monthly Payroll Processing (SRS section 34): Attendance Lock -> Apply
        OT. Sums this employee's Attendance records within the pay period into
        Overtime Hours, Worked Days, Absent Days and Total Late Minutes."""
        for rec in self:
            if not (rec.employee_id and rec.period_start and rec.period_end):
                continue
            attendances = self.env['garment.hr.attendance'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('attendance_date', '>=', rec.period_start),
                ('attendance_date', '<=', rec.period_end),
            ])
            rec.write({
                'overtime_hours': sum(attendances.mapped('overtime_hours')),
                'worked_days': len(attendances.filtered(lambda a: a.status in ('present', 'late', 'half_day'))),
                'absent_days': len(attendances.filtered(lambda a: a.status == 'absent')),
                'late_minutes_total': sum(attendances.mapped('late_minutes')),
            })

    def action_pull_bonuses_and_incentives(self):
        """Pull approved/paid garment.hr.bonus and garment.hr.incentive records
        for this employee's period into the itemised earning fields."""
        for rec in self:
            if not (rec.employee_id and rec.period_start and rec.period_end):
                continue
            bonuses = self.env['garment.hr.bonus'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('period', '>=', rec.period_start), ('period', '<=', rec.period_end),
                ('status', '!=', 'draft'),
            ])
            incentives = self.env['garment.hr.incentive'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('period_end', '>=', rec.period_start), ('period_end', '<=', rec.period_end),
                ('status', '!=', 'draft'),
            ])
            rec.write({
                'festival_bonus': sum(bonuses.filtered(lambda b: b.bonus_type == 'festival').mapped('amount')),
                'attendance_bonus': sum(bonuses.filtered(lambda b: b.bonus_type == 'attendance').mapped('amount')),
                'production_incentive_amount': sum(incentives.mapped('incentive_amount')),
            })
            bonuses.write({'payroll_id': rec.id})
            incentives.write({'payroll_id': rec.id})

    def action_hr_verify(self):
        self.write({'payment_status': 'hr_verified'})

    def action_approve(self):
        self.write({'payment_status': 'approved'})

    def action_process(self):
        self.write({'payment_status': 'processed'})

    def action_mark_paid(self):
        self.write({'payment_status': 'paid'})
