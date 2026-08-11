# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.addons.helper import validator


class WPPFPolicy(models.Model):
    _name = 'wppf.policy'
    _description = "Policy For WPPF"

    name = fields.Char(string='Name', required=True)
    fiscalyear_id = fields.Many2one('account.fiscal.year', required=True, string='Fiscal Year')

    eligibility_base = fields.Selection([('joining_date', 'Joining Date'), ('confirmation_date', 'Confirmation Date')],
                                        string="Eligibility Based On", required=True)
    min_service_length_total = fields.Integer(string='Min. Total Service Length (Month)', default=9)
    min_service_length_period = fields.Integer(string='Min. Period Service Length (Month)', default=6)

    wppf_percent = fields.Float(string='WPPF Fund/Reserve (%)', required=True, default=33.33)
    tds_type = fields.Selection([
        ('percent', 'Percent (%)'),
        ('fixed', 'Fixed'),
    ], string='TDS Type', required=True, default='percent')
    tds_percent = fields.Float(string='TDS Value', required=True, default=5)
    allow_bod = fields.Boolean(string='Is Allow BOD?', default=False)
    active = fields.Boolean(string='Active', default=True)
    wppf_user_count = fields.Integer(string='Number of WPPF Employee', default=0)

    #  accounts
    journal_id_settlement = fields.Many2one('account.journal', string='Settlement Journal',
                                            domain="[('is_wppf_display','=',True)]")

    payable_acc_id = fields.Many2one('account.account', 'Payable Account (DR)')
    reserve_acc_id = fields.Many2one('account.account', 'Reserve Account (CR)')
    loan_acc_id = fields.Many2one('account.account', 'Loan Receivable Account (CR)')
    other_acc_id = fields.Many2one('account.account', 'Other Account (CR)')

    journal_id_payment = fields.Many2one('account.journal', string='Settlement Payment Journal',
                                         domain="[('is_wppf_display','=',True)]")
    payment_acc_id = fields.Many2one('account.account', 'Payment Account (CR)')

    @api.depends('name', 'fiscalyear_id')
    def name_get(self):
        for record in self:
            return [(record.id, '{} [{}]'.format(record.name, record.fiscalyear_id.name or '')) for record in self]

    @api.constrains('fiscalyear_id')
    def _check_unique_constraint(self):
        for rec in self:
            msg = 'WPPF Policy of the Fiscal Year  "%s"' % self.fiscalyear_id.name
            envObj = self.env['wppf.policy']
            conditionList = [('fiscalyear_id', '=', self.fiscalyear_id.id)]
            validator.check_duplicate_value(self, envObj, conditionList, msg)

    def action_check_wppf_user(self):
        eligibility_based_on = self.eligibility_base
        min_service_length_total = self.min_service_length_total
        min_service_length_period = self.min_service_length_period
        allow_bod = self.allow_bod
        period_date_from = self.fiscalyear_id.date_from
        period_date_to = self.fiscalyear_id.date_to
        current_date = fields.Date.today()

        emp_obj = self.env['hr.employee'].sudo().search(['|', ('active', '=', True), ('active', '=', False)])
        wppf_user_count = 0
        for emp in emp_obj:
            emp.is_wppf_user = False
            # skip restrict and chk Board of directors
            if emp.is_wppf_restricted:
                continue
            if not allow_bod:
                if emp.is_bod:
                    continue

            initial_employment_date = emp.initial_employment_date
            date_of_confirmation = emp.date_of_confirmation

            total_service_month = 0
            period_service_month = 0
            is_valid_wppf_emp = False

            if eligibility_based_on == 'joining_date':
                if initial_employment_date and initial_employment_date < period_date_to:
                    #  total service
                    start = initial_employment_date
                    if emp.is_separated:
                        if emp.separation_date < period_date_to:
                            if emp.separation_date < period_date_from:
                                continue
                            elif emp.separation_date < start:
                                continue
                            else:
                                difference = relativedelta(emp.separation_date, start)
                        else:
                            difference = relativedelta(period_date_to, start)
                    else:
                        difference = relativedelta(period_date_to, start)
                    total_service_month = difference.months + (12 * difference.years)
                    if total_service_month >= min_service_length_total:
                        # period service
                        p_start = initial_employment_date
                        if emp.is_separated:
                            if p_start < period_date_from:
                                p_difference = relativedelta(emp.separation_date, period_date_from)
                            else:
                                p_difference = relativedelta(emp.separation_date, p_start)

                            p_months = p_difference.months + (12 * p_difference.years)
                            period_service_month = p_months
                            if period_service_month >= min_service_length_period:
                                is_valid_wppf_emp = True
                        else:
                            is_valid_wppf_emp = True
                else:
                    continue

            elif eligibility_based_on == 'confirmation_date':
                if date_of_confirmation and date_of_confirmation < period_date_to:
                    # total service
                    start = date_of_confirmation
                    if emp.is_separated:
                        if emp.separation_date < period_date_to:
                            if emp.separation_date < period_date_from:
                                continue
                            elif emp.separation_date < start:
                                continue
                            else:
                                difference = relativedelta(emp.separation_date, start)
                        else:
                            difference = relativedelta(period_date_to, start)
                    else:
                        difference = relativedelta(period_date_to, start)

                    total_service_month = difference.months + (12 * difference.years)
                    if total_service_month >= min_service_length_total:
                        # period service
                        p_start = date_of_confirmation
                        if emp.is_separated:
                            if p_start < period_date_from:
                                p_difference = relativedelta(emp.separation_date, period_date_from)
                            else:
                                p_difference = relativedelta(emp.separation_date, p_start)

                            p_months = p_difference.months + (12 * p_difference.years)
                            period_service_month = p_months
                            if period_service_month >= min_service_length_period:
                                is_valid_wppf_emp = True
                        else:
                            is_valid_wppf_emp = True

                else:
                    continue

            # valid wppf employee
            if is_valid_wppf_emp:
                emp.is_wppf_user = True
                emp.wppf_policy_id = self.id
                wppf_user_count += 1

                wppf_obj = self.env['wppf.profile'].sudo().search([('employee_id', '=', emp.id)], limit=1)
                if not wppf_obj:
                    wppf_obj.sudo().create({
                        'employee_id': emp.id,
                        'membership_date': fields.Date.today(),
                        'membership_approve_date': fields.Date.today(),
                        'is_active': True
                    })

        self.wppf_user_count = wppf_user_count


class WPPFProfitDisbConfiguration(models.Model):
    _name = "wppf.profit.disb.configuration"
    _description = "WPPF Profit Disbursement Configuration"
    _rec_name = 'disburse_journal_id'
    #  accounts
    disburse_journal_id = fields.Many2one('account.journal', string='Disburse Journal',
                                          domain="[('is_wppf_display','=',True)]", required=True)

    disburse_debit_acc_id = fields.Many2one('account.account', 'Debit Account (WPPF- Exp.)')
    disburse_fund_credit_acc_id = fields.Many2one('account.account', 'Credit Account (WPPF- Fund Payable)')
    disburse_disb_credit_acc_id = fields.Many2one('account.account', 'Credit Account (WPPF- Disburse Payable)')
    disburse_tds_credit_acc_id = fields.Many2one('account.account', 'Credit Account (WPPF- TDS Payable)')
    disburse_move_id = fields.Many2one('account.move', 'Disburse Journal Entries (Payable)')

    payment_journal_id = fields.Many2one('account.journal', string='Disbursed Payment Journal',
                                         domain="[('is_wppf_display','=',True)]", required=True)

    payment_debit_acc_id = fields.Many2one('account.account', 'Debit Account (WPPF- Disburse Payable)')
    payment_credit_acc_id = fields.Many2one('account.account', 'Credit Account (Cash/Bank)')
