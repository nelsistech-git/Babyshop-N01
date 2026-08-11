# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    strict_range = fields.Boolean(string='Use Strict Range', help='Use this if you want to show TB with retained earnings section')
    bucket_1 = fields.Integer(string='Bucket 1', required=True, default=30)
    bucket_2 = fields.Integer(string='Bucket 2', required=True, default=60)
    bucket_3 = fields.Integer(string='Bucket 3', required=True, default=90)
    bucket_4 = fields.Integer(string='Bucket 4', required=True, default=120)
    bucket_5 = fields.Integer(string='Bucket 5', required=True, default=180)
    date_range = fields.Selection(
        [('today', 'Today'),
         ('this_week', 'This Week'),
         ('this_month', 'This Month'),
         ('this_quarter', 'This Quarter'),
         ('this_financial_year', 'This financial Year'),
         ('yesterday', 'Yesterday'),
         ('last_week', 'Last Week'),
         ('last_month', 'Last Month'),
         ('last_quarter', 'Last Quarter'),
         ('last_financial_year', 'Last Financial Year')],
        string='Default Date Range', default='this_financial_year', required=True
    )
    financial_year = fields.Selection([
        ('april_march','1 April to 31 March'),
        ('july_june','1 July to 30 June'),
        ('january_december','1 Jan to 31 Dec')
        ], string='Financial Year', default='january_december', required=True)


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    excel_format = fields.Char(string='Excel format', default='_ * #,##0.00_) ;_ * - #,##0.00_) ;_ * "-"??_) ;_ @_ ', required=True)

class InheritedAccountFinancialReport(models.Model):
    _inherit = "account.financial.report"
    _description = "Account Report"

    z_view_rule = fields.Selection([
        ('blank', 'Blank'),
        ('dash', 'Dash(-)'),
    ], 'Zero View Rule', default='blank', help="Zero value print rule in report")
    sum_reports = fields.One2many('fr.sum.line', 'acc_report_id',
                                  string='FR Report Line', copy=True, auto_join=True)
    border_top = fields.Boolean('Border Top', default=False)
    border_left = fields.Boolean('Border Left', default=False)
    border_bottom = fields.Boolean('Border Bottom', default=False)
    border_right = fields.Boolean('Border Right', default=False)
    border_bottom_double = fields.Boolean('Border Bottom Double', default=False)
    remarks = fields.Char('Remarks')
    notes = fields.Float('Notes')

# class AccountAccount(models.Model):
#     _inherit = 'account.account'
#
#     def get_cashflow_domain(self):
#         cash_flow_id = self.env.ref('dynamic_accounts_report.ins_account_financial_report_cash_flow0')
#         if cash_flow_id:
#             return [('parent_id.id', '=', cash_flow_id.id)]
#
#     cash_flow_category = fields.Many2one('account.financial.report', string="Cash Flow type", domain=get_cashflow_domain)
#
#     @api.onchange('cash_flow_category')
#     def onchange_cash_flow_category(self):
#         # Add account to cash flow record to account_ids
#         if self._origin and self._origin.id:
#             self.cash_flow_category.write({'account_ids': [(4, self._origin.id)]})
#             self.env.ref(
#                 'dynamic_accounts_report.ins_account_financial_report_cash_flow0').write(
#                 {'account_ids': [(4, self._origin.id)]})
#         # Remove account from previous category
#         # In case of changing/ removing category
#         if self._origin.cash_flow_category:
#             self._origin.cash_flow_category.write({'account_ids': [(3, self._origin.id)]})
#             self.env.ref(
#                 'dynamic_accounts_report.ins_account_financial_report_cash_flow0').write(
#                 {'account_ids': [(3, self._origin.id)]})
#
#     report_by = fields.Selection([
#         ('debit', 'Debit'),
#         ('credit', 'Credit'),
#         ('balance', 'Balance'),
#     ], 'Report By', default='debit')


class FRSumLine(models.Model):
    _name = "fr.sum.line"
    _description = "FR Summation Line"

    acc_report_id = fields.Many2one('account.financial.report', string='Accounting Report', ondelete='cascade', index=True, copy=False)
    report = fields.Many2one('account.financial.report', string='Report Name')