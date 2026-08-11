# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import random
import math
import pytz
import json

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.exceptions import AccessError
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)

MONTH = {
    1: 'Jan',
    2: 'Feb',
    3: 'Mar',
    4: 'Apr',
    5: 'May',
    6: 'Jun',
    7: 'Jul',
    8: 'Aug',
    9: 'Sep',
    10: 'Oct',
    11: 'Nov',
    12: 'Dec',
}


class SSPReviewDashboard(models.Model):
    _name = 'ssp.review.dashboard'
    _description = 'Management Review Dashboard'

    # Digest description
    name = fields.Char(string='Name', required=True, translate=True)
    periodicity = fields.Selection([('daily', 'Daily'),
                                    ('weekly', 'Weekly'),
                                    ('monthly', 'Monthly'),
                                    ('quarterly', 'Quarterly')],
                                   string='Periodicity', default='daily', required=True)
    start_date = fields.Char('Start Date', compute="get_dashbaord_data")
    end_date = fields.Char('End date', compute="get_dashbaord_data")
    ### Sales
    total_invoice_amount = fields.Char(string="Total Invoice Amount", compute="get_dashbaord_data")
    total_invoice_due_amount = fields.Char(string="Total Invoice Due Amount", compute="get_dashbaord_data")
    total_invoice_received_amount = fields.Char(string="Total Invoice Received Amount", compute="get_dashbaord_data")
    total_received_payment_amount = fields.Char(string="Total Received Payment Amount", compute="get_dashbaord_data")
    total_due_collection_amount = fields.Char(string="Total Due Collection Amount", compute="get_dashbaord_data")
    total_invoice_refund_amount = fields.Char(string="Total Due Collection Amount", compute="get_dashbaord_data")
    #### Purchase
    total_bill_amount = fields.Char(string="Total Bill Amount", compute="get_dashbaord_data")
    total_bill_due_amount = fields.Char(string="Total Bill Due Amount", compute="get_dashbaord_data")
    total_bill_paid_amount = fields.Char(string="Total Bill Paid Amount", compute="get_dashbaord_data")
    total_payment_amount = fields.Char(string="Total Payment Amount", compute="get_dashbaord_data")
    total_due_paid_amount = fields.Char(string="Total Due Paid Amount", compute="get_dashbaord_data")
    total_bill_refund_amount = fields.Char(string="Total Bill Refund Amount", compute="get_dashbaord_data")
    ### Stock
    cost_of_good_sold = fields.Char(string="Cost of Good Sold", compute="get_dashbaord_data")
    current_stock_value = fields.Char(string="Current Stock value", compute="get_dashbaord_data")
    ## account
    cash_at_bank = fields.Char(string="Cash At Bank", compute="get_dashbaord_data")
    cash_in_hand = fields.Char(string="Cash In Hand", compute="get_dashbaord_data")
    total_income = fields.Char(string="total_income", compute="get_dashbaord_data")
    total_expense = fields.Char(string="Expense", compute="get_dashbaord_data")
    total_revenue = fields.Char(string="total_revenue", compute="get_dashbaord_data")
    company_id = fields.Many2one('res.company', string="Company", compute="get_dashbaord_data")
    receivable = fields.Char(string="receivable", compute="get_dashbaord_data")
    payable = fields.Char(string="payable", compute="get_dashbaord_data")

    company_statistics = fields.Text(string="Company Statistics", compute="_compute_dashboard_data")
    balance = fields.Float(string="Difference", compute="_compute_dashboard_data")
    total_asset = fields.Float(string="Difference", compute="_compute_dashboard_data")
    total_investment = fields.Float(string="Difference", compute="_compute_dashboard_data")
    latest_addition = fields.Float(string="Difference", compute="_compute_dashboard_data")

    def get_line_graph_datas(self):
        end_date = fields.Date.today()
        start_date = end_date - relativedelta(months=3)
        company_list = self.env['res.company'].sudo().search([('id', 'child_of', self.env.company.id)]).ids
        asset_graph_data = []
        investment_graph_data = []
        # Company Value asset
        assets_group = ["asset_fixed", "asset_non_current", "asset_cash", "liability_credit_card", "asset_current",
                        "asset_receivable", "asset_prepayments"]
        total_value = 0
        company_data = dict()
        investment = 0
        investment_data = dict()
        for company in company_list:
            initial_all_data = self.env['account.move.line'].sudo().with_company(company).search(
                [('company_id', '=', company), ('account_id.account_type', 'in', assets_group),
                 ('date', "<", start_date)], order='date')
            for item in initial_all_data:
                if item.move_id.state == "posted":
                    total_value += (item.debit - item.credit)

            company_value_datas = self.env['account.move.line'].sudo().with_company(company).search(
                [('company_id', '=', company), ('account_id.account_type', 'in', assets_group),
                 ('date', ">=", start_date), ('date', '<=', end_date)], order='date')
            for value_line in company_value_datas:
                if value_line.move_id.state == "posted":
                    if value_line.date not in company_data.keys():
                        company_data[value_line.date] = 0
                    company_data[value_line.date] += (value_line.debit - value_line.credit)

            # Investment

            initial_investment_datas = self.env['account.move.line'].sudo().with_company(company).search(
                [('company_id', '=', company), ('account_id.is_investment', '=', True), ('date', "<", start_date)],
                order='date')
            for item in initial_investment_datas:
                if item.move_id.state == "posted":
                    investment += (item.credit - item.debit)
            investment_datas = self.env['account.move.line'].sudo().with_company(company).search(
                [('company_id', '=', company), ('account_id.is_investment', '=', True), ('date', ">=", start_date),
                 ('date', '<=', end_date)], order='date')
            for item in investment_datas:
                if item.move_id.state == "posted":
                    if item.date not in investment_data.keys():
                        investment_data[item.date] = 0
                    investment_data[item.date] += (item.credit - item.debit)

        second_end_date = end_date - relativedelta(days=1)
        second_end_value = end_value = 0
        self.latest_addition = 0
        # Calculate Graph
        current_date = start_date
        while current_date <= end_date:
            if current_date in company_data.keys():
                total_value += company_data[current_date]

            if current_date in investment_data.keys():
                investment += investment_data[current_date]

            d = current_date.day
            m = current_date.month
            asset_graph_data.append({'x': str(d) + "-" + MONTH[m], 'y': round(total_value, 2),
                                    'name': str(d) + "-" + MONTH[m] + " | " + str(round(total_value, 2))})
            investment_graph_data.append({'x': str(d) + "-" + MONTH[m], 'y': round(investment, 2),
                                        'name': str(d) + "-" + MONTH[m] + " | " + str(round(investment, 2))})

            if end_date == current_date:
                end_value = total_value
                if current_date in company_data.keys():
                    self.latest_addition = round(company_data[current_date], 2)
            if second_end_date == current_date:
                second_end_value = total_value

            current_date = current_date + relativedelta(days=1)

        self.balance = round(end_value - second_end_value, 2)
        self.total_asset = round(total_value, 2)
        self.total_investment = round(investment, 2)

        [asset_graph_title, asset_graph_key] = ['', _('Company Asset Value')]
        [investment_graph_title, investment_graph_key] = ['', _('Investment')]

        company_color = 'green'

        return [
            {'values': asset_graph_data, "theme": "light2", 'title': asset_graph_title, 'key': asset_graph_key,
            'area': True, 'color': company_color},
            {'values': investment_graph_data, "theme": "light2", 'title': investment_graph_title,
            'key': investment_graph_key, 'area': True, 'color': company_color}
        ]

    def _compute_dashboard_data(self):
        self.company_statistics = json.dumps(self.get_line_graph_datas())

    def get_dashbaord_data(self):
        end_date = fields.Date.today()
        company_id = self.env.company
        # start_date = fields.Date.from_string('2021-04-06')
        for dashboard in self:
            if self._context.get('have_date_range'):
                end_date = fields.Date.from_string(self._context.get('end_date'))
                start_date = fields.Date.from_string(self._context.get('start_date'))
            else:
                periodicity = self._context.get('periodicity')
                if periodicity == 'daily':
                    start_date = end_date
                elif periodicity == 'weekly':
                    start_date = end_date - relativedelta(weeks=1)
                elif periodicity == 'monthly':
                    start_date = end_date - relativedelta(months=1)
                elif periodicity == 'quarterly':
                    start_date = end_date - relativedelta(months=3)

            # print("\n\n",periodicity," ", start_date, " ", end_date)
            dashboard.company_id = company_id.id
            dashboard.start_date = start_date
            dashboard.end_date = end_date
            ssp_review = self.env['ssp.review'].search([], limit=1)
            all_sales_data = ssp_review.compute_sales_data(False, start_date, end_date)
            dashboard.total_invoice_amount = all_sales_data['total_invoice_amount']
            dashboard.total_invoice_due_amount = all_sales_data['total_invoice_due_amount']
            dashboard.total_invoice_received_amount = all_sales_data['total_invoice_received_amount']
            dashboard.total_received_payment_amount = all_sales_data['total_received_payment_amount']
            dashboard.total_due_collection_amount = all_sales_data['total_due_collection_amount']
            dashboard.total_invoice_refund_amount = all_sales_data['total_invoice_refund_amount']

            all_purchase_data = ssp_review.compute_purchase_data(False, start_date, end_date)
            dashboard.total_bill_amount = all_purchase_data['total_bill_amount']
            dashboard.total_bill_due_amount = all_purchase_data['total_bill_due_amount']
            dashboard.total_bill_paid_amount = all_purchase_data['total_bill_paid_amount']
            dashboard.total_payment_amount = all_purchase_data['total_payment_amount']
            dashboard.total_due_paid_amount = all_purchase_data['total_due_paid_amount']
            dashboard.total_bill_refund_amount = all_purchase_data['total_bill_refund_amount']

            cost_of_good_sold = 0
            # company_list = request.env['res.company'].sudo().search([('id', 'child_of', company_id)]).ids
            # for company in company_list:
            #     account_type = self.env['account.account.type'].search([['name', '=', 'Cost of Revenue']]).id
            #     account_ids = self.env['account.account'].sudo().with_company(company).search([('company_id', '=', company), ['user_type_id', '=', account_type]]).ids
            #     all_filtered_journal_items = self.env['account.move.line'].sudo().with_company(company).search([('company_id', '=', company), ['account_id', 'in', account_ids], ['date', '>=', start_date], ['date', '<=', end_date]])
            #
            #     for item in all_filtered_journal_items:
            #         if item.move_id.state == "posted":
            #             cost_of_good_sold += (item.debit - item.credit)

            all_account_data = ssp_review.compute_account_data(False, start_date, end_date)
            # dashboard.cost_of_good_sold = 45280.18
            # dashboard.total_revenue = 7772.25
            dashboard.cost_of_good_sold = all_account_data['cost_of_good_sold']
            dashboard.total_income = all_account_data['total_income']
            dashboard.total_expense = all_account_data['total_expense']
            dashboard.total_revenue = all_account_data['total_revenue']


            all_balance_data = ssp_review.compute_balance_data(False, start_date, end_date)
            dashboard.cash_at_bank = all_balance_data['cash_at_bank']
            dashboard.cash_in_hand = all_balance_data['cash_in_hand']
            dashboard.current_stock_value = all_balance_data['current_stock_value']
            dashboard.receivable = all_balance_data['receivable']
            dashboard.payable = all_balance_data['payable']

    def generate_summary_data(self):
        self.env.cr.execute(""" TRUNCATE TABLE ssp_review_cab; """)
        self.env.cr.execute(""" TRUNCATE TABLE ssp_review_cih; """)
        self.env.cr.execute(""" TRUNCATE TABLE ssp_review_csv; """)
        self.env.cr.execute(""" TRUNCATE TABLE ssp_review_expense; """)
        self.env.cr.execute(""" TRUNCATE TABLE ssp_review_income; """)
        self.env.cr.execute(""" TRUNCATE TABLE ssp_review_cogs; """)
        self.env.cr.execute(""" TRUNCATE TABLE ssp_review_receivable; """)
        self.env.cr.execute(""" TRUNCATE TABLE ssp_review_payable; """)
        company_ids = self.env['res.company'].sudo().search([])
        for company_id in company_ids:
            all_journals = self.env['account.move'].sudo().with_company(company_id.id).search(
                [('company_id', '=', company_id.id), ('state', '=', 'posted')])
            for journal in all_journals:
                for item in journal.line_ids:
                    item.with_company(company_id.id).dashboard_entry(item.date, item.account_id,
                                                                     (item.debit - item.credit))

        return {
            'name': "Management Review Dashboard",
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,form',
            'res_model': 'ssp.review.dashboard',
            'res_id': self.env.ref("management_review.ssp_review_dashboard_daily").id
        }


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft)
        for item in self.line_ids:
            item.dashboard_entry(item.date, item.account_id, (item.debit - item.credit))
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for item in self.line_ids:
            item.dashboard_entry(item.date, item.account_id, (item.credit - item.debit))
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def dashboard_entry(self, date, account_id, value):
        if self.product_id and self.account_id.id == self.product_id.categ_id.property_stock_valuation_account_id.id:
            last_record = self.env['ssp.review.csv'].sudo().search([('company_id', '=', self.company_id.id)], limit=1)
            if not last_record:
                self.env['ssp.review.csv'].sudo().create({
                    'date': date,
                    'total_value': value,
                    'company_id': self.company_id.id
                })
            else:
                last_record.sudo().write({
                    'total_value': (last_record.total_value + value)
                })

        if account_id.account_type== "expense_direct_cost":
            last_record = self.env['ssp.review.cogs'].sudo().search(
                [('company_id', '=', self.company_id.id), ('date', '=', date)], limit=1)
            if not last_record:
                self.env['ssp.review.cogs'].sudo().create({
                    'date': date,
                    'total_value': value,
                    'company_id': self.company_id.id
                })
            else:
                last_record.sudo().write({
                    'total_value': (last_record.total_value + value)
                })

        if account_id.account_type == "liability_payable":
            last_record = self.env['ssp.review.payable'].sudo().search([('company_id', '=', self.company_id.id)],
                                                                       limit=1)
            if not last_record:
                self.env['ssp.review.payable'].sudo().create({
                    'date': date,
                    'total_value': value * (-1),
                    'company_id': self.company_id.id
                })
            else:
                last_record.sudo().write({
                    'total_value': (last_record.total_value + (value * (-1)))
                })

        if account_id.account_type == "asset_receivable":
            last_record = self.env['ssp.review.receivable'].sudo().search([('company_id', '=', self.company_id.id)],
                                                                          limit=1)
            if not last_record:
                self.env['ssp.review.receivable'].sudo().create({
                    'date': date,
                    'total_value': value,
                    'company_id': self.company_id.id
                })
            else:
                last_record.sudo().write({
                    'total_value': (last_record.total_value + value)
                })

        if account_id.account_type in ["income", "income_other"]:
            last_record = self.env['ssp.review.income'].sudo().search(
                [('company_id', '=', self.company_id.id), ('date', '=', date)], limit=1)
            if not last_record:
                self.env['ssp.review.income'].sudo().create({
                    'date': date,
                    'total_value': value * (-1),
                    'company_id': self.company_id.id
                })
            else:
                last_record.sudo().write({
                    'total_value': (last_record.total_value + (value * (-1)))
                })
        if account_id.account_type in ["expense", "expense_depreciation"]:
            last_record = self.env['ssp.review.expense'].sudo().search(
                [('company_id', '=', self.company_id.id), ('date', '=', date)], limit=1)
            if not last_record:
                self.env['ssp.review.expense'].sudo().create({
                    'date': date,
                    'total_value': value,
                    'company_id': self.company_id.id
                })
            else:
                last_record.sudo().write({
                    'total_value': (last_record.total_value + value)
                })

        bank_accounts = list()
        cash_accounts = list()
        all_journals = self.env['account.journal'].sudo().search([('company_id', '=', self.company_id.id)])
        for journal in all_journals:
            if journal.type == 'bank':
                bank_accounts.append(journal.default_account_id.id)
                # bank_accounts.append(journal.payment_debit_account_id.id)
                # bank_accounts.append(journal.payment_credit_account_id.id)
            if journal.type == 'cash':
                cash_accounts.append(journal.default_account_id.id)
                # cash_accounts.append(journal.payment_debit_account_id.id)
                # cash_accounts.append(journal.payment_credit_account_id.id)
        if account_id.id in cash_accounts:
            last_record = self.env['ssp.review.cih'].sudo().search([('company_id', '=', self.company_id.id)], limit=1)
            if not last_record:
                self.env['ssp.review.cih'].sudo().create({
                    'date': date,
                    'total_value': value,
                    'company_id': self.company_id.id
                })
            else:
                last_record.sudo().write({
                    'total_value': (last_record.total_value + value)
                })
        if account_id.id in bank_accounts:
            last_record = self.env['ssp.review.cab'].sudo().search([('company_id', '=', self.company_id.id)], limit=1)
            if not last_record:
                self.env['ssp.review.cab'].sudo().create({
                    'date': date,
                    'total_value': value,
                    'company_id': self.company_id.id
                })
            else:
                last_record.sudo().write({
                    'total_value': (last_record.total_value + value)
                })


class SSPReviewCOGS(models.Model):
    _name = 'ssp.review.cogs'
    _description = 'ssp Reveiw Cost of Good Sold'

    date = fields.Date('Date')
    total_value = fields.Float("Value")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)


class SSPReviewIncome(models.Model):
    _name = 'ssp.review.income'
    _description = 'SSP Reveiw Income'

    date = fields.Date('Date')
    total_value = fields.Float("Value")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)


class SSPReviewExpense(models.Model):
    _name = 'ssp.review.expense'
    _description = 'SSP Reveiw Expense'

    date = fields.Date('Date')
    total_value = fields.Float("Value")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)


class SSPReviewCSV(models.Model):
    _name = 'ssp.review.csv'
    _description = 'ssp Reveiw current stock value'

    date = fields.Date('Date')
    total_value = fields.Float("Value")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)


class SSPReviewCIH(models.Model):
    _name = 'ssp.review.cih'
    _description = 'ssp Reveiw Cash IN Hand'

    date = fields.Date('Date')
    total_value = fields.Float("Value")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)


class SSPReviewCAT(models.Model):
    _name = 'ssp.review.cab'
    _description = 'ssp Reveiw Cash at Bank'

    date = fields.Date('Date')
    total_value = fields.Float("Value")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)


class SSPReviewPayable(models.Model):
    _name = 'ssp.review.payable'
    _description = 'ssp Reveiw Payable'

    date = fields.Date('Date')
    total_value = fields.Float("Value")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)


class SSPReviewReceivable(models.Model):
    _name = 'ssp.review.receivable'
    _description = 'ssp Reveiw Receivable'

    date = fields.Date('Date')
    total_value = fields.Float("Value")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)


class DashboardRefresh(models.TransientModel):
    _name = 'ssp.review.dashboard.refresh'

    def re_calculate_dashboard_data(self):
        dashboard = self.env['ssp.review.dashboard'].search([], limit=1)
        dashboard.generate_summary_data()


class DashboardCustomDate(models.TransientModel):
    _name = 'ssp.review.dashboard.custom.date'

    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')

    def calculate_custom_date_wise_data(self):
        return {
            'name': _('Management Review Dashboard from %s to %s' % (self.start_date, self.end_date)),
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban',
            'res_model': 'ssp.review.dashboard',
            'view_id': self.env.ref("management_review.ssp_reveiw_kanban").id,
            'res_id': self.env.ref('management_review.ssp_review_dashboard_daily').id,
            'context': {'have_date_range': True, 'start_date': self.start_date, 'end_date': self.end_date}
        }
