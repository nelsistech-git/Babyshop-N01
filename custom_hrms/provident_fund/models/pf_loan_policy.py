# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PFLoanPolicy(models.Model):
    _name = 'pf.loan.policy'
    _description = "Policy For Provident Fund Loan"

    loan_eligibility_selection = [('membership_date', 'Membership Date'), ('joining_date', 'Joining Date'), ('confirmation_date', 'Confirmation Date')]
    duration_type_selection = [('day', 'Day'), ('month', 'Month'), ('year', 'Year')]
    loan_amount_source_selection = [('emp_plus_comp_por', 'Employee and Company Portion'), ('employee', 'Employee Contribution'), ('both', 'Both Contribution')]

    name = fields.Char(string='Name', required=True)
    loan_eligibility_base = fields.Selection(selection=loan_eligibility_selection, string="Eligibility Based On", required=True)
    loan_amount_source = fields.Selection(selection=loan_amount_source_selection, string="Loan Amount Source", required=True)
    duration_type = fields.Selection(selection=duration_type_selection, string='Duration Type', required=True)
    loan_eligibility_duration = fields.Integer(string='Eligibility Duration', required=True)
    loan_interest = fields.Float(string='Loan Interest (%)', required=True)
    loan_policy_line = fields.One2many(comodel_name='pf.loan.policy.line', inverse_name='pf_loan_policy_id', string='Eligible Configuration')

    minimum_loan_amount = fields.Float(string="Minimum Loan Amount", default=0.0)
    month_gap_loan = fields.Integer(string="Month Gap For Loan", default=1)
    max_no_installment = fields.Integer(string="Max No. of Installment", default=1)
    minimum_installment_amount = fields.Float(string="Installment min amount", default=0.0)


    _sql_constraints = [('no_zero_negative_installment', 'CHECK(max_no_installment <= 0)', 'Max no of installment must be greater than Zero.')]


class PFLoanPolicyLine(models.Model):
    _name = 'pf.loan.policy.line'
    _description = "Policy For Provident Fund Loan"

    pf_loan_policy_id = fields.Many2one(comodel_name='pf.loan.policy', string='Loan Policy', required=True, ondelete='cascade')
    from_month = fields.Integer(string='From', required=True)
    to_month = fields.Integer(string='To', required=True)
    # loan_interest = fields.Float(string='Loan Interest (%)', required=True)
    loan_max_percent = fields.Float(string='Max Loan Percentage (%)', required=True)

    @api.onchange('loan_max_percent')
    def _onchange_loan_max_percent(self):
        for record in self:
            if record.loan_max_percent and record.loan_max_percent > 100:
                record.loan_max_percent = 0
                return UserError(message=_("Loan max percentage can not be grater than 100"), title=_("Data Error"))
