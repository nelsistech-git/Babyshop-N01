# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math
import pytz
import re
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.exceptions import AccessError
# from odoo.tools.float_utils import float_round
from odoo.tools import float_compare, float_round, float_repr


_logger = logging.getLogger(__name__)



class SSPReview(models.Model):
    _name = 'ssp.review'
    _description = 'Management Review'

    # Digest description
    name = fields.Char(string='Name', required=True, translate=True)
    user_ids = fields.Many2many('res.users', string='Recipients', domain="[('share', '=', False)]")
    periodicity = fields.Selection([('daily', 'Daily'),
                                    ('weekly', 'Weekly'),
                                    ('monthly', 'Monthly'),
                                    ('quarterly', 'Quarterly')],
                                   string='Periodicity', default='daily', required=True)
    next_run_date = fields.Date(string='Next Send Date')
    template_id = fields.Many2one('mail.template', string='Email Template',
                                  domain="[('model','=','ssp.review')]",
                                  default=lambda self: self.env.ref('management_review.ssp_review_mail_template'),
                                  required=True)
    currency_id = fields.Many2one(related="company_id.currency_id", string='Currency', readonly=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    state = fields.Selection([('activated', 'Activated'), ('deactivated', 'Deactivated')], string='Status', readonly=True, default='activated')
    


    @api.onchange('periodicity')
    def _onchange_periodicity(self):
        self.next_run_date = self._get_next_run_date()

    @api.model
    def create(self, vals):
        vals['next_run_date'] = date.today() + relativedelta(days=3)
        return super(SSPReview, self).create(vals)

    def action_activate(self):
        self.state = 'activated'


    def action_deactivate(self):
        self.state = 'deactivated'



    # def action_send(self):
    #     for ssp in self:
    #         for user in ssp.user_ids:
    #             subject = '%s: %s' % (self.company_id.name, ssp.name)
    #             ssp.template_id.with_context(user=user).send_mail(ssp.id, force_send=True, raise_exception=True, email_values={'email_to': user.email, 'subject': subject})
    #         ssp.next_run_date = ssp._get_next_run_date()
    
    def action_send(self):
        for ssp in self:
            for user in ssp.user_ids:
                subject = '%s: %s' % (self.company_id.name, ssp.name)
                email_to = user.email
                email_from = self.env['ir.config_parameter'].sudo().get_param('mail.default.from', default='no-reply@example.com')
                
                if not email_from or not re.match(r"[^@]+@[^@]+\.[^@]+", email_from):
                    raise ValueError("Invalid 'From' email address: %s" % email_from)

                if not email_to or not re.match(r"[^@]+@[^@]+\.[^@]+", email_to):
                    raise ValueError("Invalid 'To' email address: %s" % email_to)

                email_values = {
                    'email_to': email_to,
                    'subject': subject,
                    'email_from': email_from
                }

                ssp.template_id.with_context(user=user).send_mail(
                    ssp.id, 
                    force_send=True, 
                    raise_exception=True, 
                    email_values=email_values
                )

            ssp.next_run_date = ssp._get_next_run_date()

    def get_company_list(self, company_id):
        if not company_id:
            company_id = self.env.company
        company_ids = self.env['res.company'].search([('id','child_of',company_id.id)]).ids
        return company_ids


    def compute_sales_data(self, company_id=False, start_date=False, end_date=False):
        self.ensure_one()
        res = {}
        if not start_date:
            start_date, end_date = self.get_time_range()
        
        res['total_invoice_amount'] = 0.0
        res['total_invoice_due_amount'] = 0.0
        res['total_invoice_received_amount'] = 0.0
        res['total_invoice_refund_amount'] = 0.0
        res['total_received_payment_amount'] = 0.0
        res['total_due_collection_amount'] = 0.0
        company_list = self.get_company_list(company_id)
        for company in company_list:
            all_invoices = self.env['account.move'].with_company(company).search([('company_id','=',company),('invoice_date','>=',start_date),('invoice_date','<=',end_date),('state','in',['posted']),('move_type','=','out_invoice')])
            invoice_number_list = list()
            total_invoice_amount = 0
            total_invoice_due_amount = 0
            for invoice in all_invoices:
                total_invoice_amount += invoice.amount_total
                total_invoice_due_amount += invoice.amount_residual
                invoice_number_list.append(invoice.name)

            res['total_invoice_amount'] += round(total_invoice_amount,2)
            res['total_invoice_due_amount'] += round(total_invoice_due_amount,2)
            #res['total_invoice_received_amount'] += float('%.2f' % (total_invoice_amount - total_invoice_due_amount))
            all_invoices = self.env['account.move'].with_company(company).search([('company_id','=',company),('invoice_date','>=',start_date),('invoice_date','<=',end_date),('state','in',['posted']),('move_type','=','out_refund')])
            total_invoice_refund_amount = 0
            for invoice in all_invoices:
                total_invoice_refund_amount += invoice.amount_total
            res['total_invoice_refund_amount'] += round(total_invoice_refund_amount,2)
            all_received_payments = self.env['account.payment'].with_company(company).search([('company_id','=',company),('date','<=',str(end_date)),('date','>=',str(start_date)),('payment_type','=','inbound'),('partner_type','=','customer'),('state','in',['posted'])])
            total_received_payment_amount = 0
            total_invoice_return = 0
            for payment in all_received_payments:
                total_received_payment_amount += payment.amount
            res['total_received_payment_amount'] += round(total_received_payment_amount,2)
            all_received_payments = self.env['account.payment'].with_company(company).search([('company_id','=',company),('date','<=',str(end_date)),('date','>=',str(start_date)),('payment_type','=','inbound'),('state','in',['posted'])])
            total_due_collection_amount = 0
            for payment in all_received_payments:
                # invoice_id = payment.reconciled_invoice_ids[0]
                for invoice_id in payment.reconciled_invoice_ids:
                    payment_amount = invoice_id.amount_total - invoice_id.amount_residual
                    payment_lines = invoice_id._get_reconciled_invoices_partials()
                    for line in payment_lines:
                        if len(line) > 2 and hasattr(line[2], 'payment_id') and line[2].payment_id.id == payment.id:
                            payment_amount = line[1]
                    if invoice_id and fields.Date.from_string(invoice_id.invoice_date) < start_date:
                        total_due_collection_amount += payment_amount
                    if invoice_id and fields.Date.from_string(invoice_id.invoice_date) >= start_date and fields.Date.from_string(invoice_id.invoice_date) <= end_date:
                        res['total_invoice_received_amount'] += round(payment_amount,2)
            res['total_due_collection_amount'] += round(total_due_collection_amount if total_due_collection_amount > 0 else 0, 2)
            # print("Sale \n",res)
            # a_i_p = self.env['account.partial.reconcile'].search([('')])

        res['total_invoice_amount'] = round(res['total_invoice_amount'] ,2)
        res['total_invoice_due_amount'] = round(res['total_invoice_due_amount'],2)
        res['total_invoice_received_amount'] = round(res['total_invoice_received_amount'],2)
        res['total_invoice_refund_amount'] = round(res['total_invoice_refund_amount'],2)
        res['total_received_payment_amount'] = round(res['total_received_payment_amount'],2)
        res['total_due_collection_amount'] = round(res['total_due_collection_amount'],2)

        return res


    def compute_purchase_data(self, company_id=False, start_date=False, end_date=False):
        self.ensure_one()
        res = {}
        if not start_date:
            start_date, end_date = self.get_time_range()
        res['total_bill_amount'] = 0.0
        res['total_bill_due_amount'] = 0.0
        res['total_bill_paid_amount'] = 0.0
        res['total_bill_refund_amount'] = 0.0
        res['total_payment_amount'] = 0.0
        res['total_due_paid_amount'] = 0.0
        company_list = self.get_company_list(company_id)
        for company in company_list:
            all_invoices = self.env['account.move'].with_company(company).search([('company_id','=',company),('invoice_date','<=',end_date),('invoice_date','>=',start_date),('state','in',['posted']),('move_type','=','in_invoice')])
            total_bill_amount = 0
            total_bill_due_amount = 0
            for invoice in all_invoices:
                total_bill_amount += invoice.amount_total
                total_bill_due_amount += invoice.amount_residual

            res['total_bill_amount'] += round(total_bill_amount,2)
            res['total_bill_due_amount'] += round(total_bill_due_amount,2)
            # res['total_bill_paid_amount'] += float('%.2f' % (total_bill_amount - total_bill_due_amount))
            all_invoices = self.env['account.move'].with_company(company).search([('company_id','=',company),('invoice_date','<=',end_date),('invoice_date','>=',start_date),('state','in',['posted']),('move_type','=','in_refund')])
            total_bill_refund_amount = 0
            for invoice in all_invoices:
                total_bill_refund_amount += invoice.amount_total
            res['total_bill_refund_amount'] += round(total_bill_refund_amount,2)
            all_payment_amounts = self.env['account.payment'].with_company(company).search([('company_id','=',company),('date','<=',str(end_date)),('date','>=',str(start_date)),('payment_type','=','outbound'),('partner_type','=','supplier'),('state','in',['posted'])])
            total_payment_amount = 0
            for payment in all_payment_amounts:
                total_payment_amount += payment.amount
            res['total_payment_amount'] += round(total_payment_amount,2)
            all_received_payments = self.env['account.payment'].with_company(company).search([('company_id','=',company),('date','<=',end_date),('date','>=',start_date),('payment_type','=','outbound'),('state','in',['posted'])])
            total_due_paid_amount = 0
            for payment in all_received_payments:
                # invoice_id = payment.reconciled_bill_ids
                for invoice_id in payment.reconciled_bill_ids:
                    payment_amount = invoice_id.amount_total - invoice_id.amount_residual
                    payment_lines = invoice_id._get_reconciled_invoices_partials()
                    for line in payment_lines:
                        for line in payment_lines:
                            if len(line) > 2 and line[2].payment_id.id == payment.id:
                                payment_amount = line[1]
                    if invoice_id and fields.Date.from_string(invoice_id.invoice_date) < start_date:
                        total_due_paid_amount += payment_amount
                    if invoice_id and  fields.Date.from_string(invoice_id.invoice_date) >= start_date and fields.Date.from_string(invoice_id.invoice_date) <= end_date:
                        res['total_bill_paid_amount'] += round(payment_amount,2)
            res['total_due_paid_amount'] += round(total_due_paid_amount if total_due_paid_amount > 0 else 0, 2)
        
        res['total_bill_amount'] = round(res['total_bill_amount'],2)
        res['total_bill_due_amount'] = round(res['total_bill_due_amount'],2)
        res['total_bill_paid_amount'] = round(res['total_bill_paid_amount'],2)
        res['total_bill_refund_amount'] = round(res['total_bill_refund_amount'],2)
        res['total_payment_amount'] = round(res['total_payment_amount'],2)
        res['total_due_paid_amount'] = round(res['total_due_paid_amount'],2)
        return res
    

    def compute_account_data(self, company_id=False, start_date=False, end_date=False):
        self.ensure_one()
        res = {}
        if not start_date:
            start_date, end_date = self.get_time_range()

        res['total_income'] = 0.0
        res['total_expense'] = 0.0
        res['cost_of_good_sold'] = 0.0
        res['total_revenue'] = 0.0
        company_list = self.get_company_list(company_id)
        for company in company_list:
            
            ######## Account Cost of Revenue
            income = 0
            summary_lines = self.env['ssp.review.income'].with_company(company).search([('date','>=',start_date),('date','<=',end_date)])
            for line in summary_lines:
                income += line.total_value
            
            expense = 0
            summary_lines = self.env['ssp.review.expense'].with_company(company).search([('date','>=',start_date),('date','<=',end_date)])
            for line in summary_lines:
                expense += line.total_value
            
            cost_of_good_sold = 0
            summary_lines = self.env['ssp.review.cogs'].with_company(company).search([('date','>=',start_date),('date','<=',end_date)])
            for line in summary_lines:
                cost_of_good_sold += line.total_value
            
            cost_of_revenue = income - (expense + cost_of_good_sold)

            res['total_income'] += round(income,2)
            res['total_expense'] += round(expense,2)
            res['cost_of_good_sold'] += round(cost_of_good_sold,2)
            res['total_revenue'] += round(cost_of_revenue,2)

        return res


    def compute_balance_data(self, company_id=False, start_date=False, end_date=False):
        self.ensure_one()
        res = {}
        if not start_date:
            start_date, end_date = self.get_time_range()
        
        res['current_stock_value'] = 0.0
        res['cash_in_hand'] = 0.0
        res['cash_at_bank'] = 0.0
        res['receivable'] = 0.0
        res['payable'] = 0.0
        company_list = self.get_company_list(company_id)
        print('company_list',company_list)
        for company in company_list:

            ######## Account Cost of Revenue
            stock = 0
            summary_lines = self.env['ssp.review.csv'].with_company(company).search([])
            for line in summary_lines:
                stock += line.total_value
            
            cash_in_hand = 0
            summary_lines = self.env['ssp.review.cih'].with_company(company).search([])
            for line in summary_lines:
                cash_in_hand += line.total_value
            
            cash_at_bank = 0
            summary_lines = self.env['ssp.review.cab'].with_company(company).search([])
            for line in summary_lines:
                cash_at_bank += line.total_value
            
            receivable = 0
            summary_lines = self.env['ssp.review.receivable'].with_company(company).search([])
            print('summary_lines',summary_lines)
            for line in summary_lines:
                receivable += line.total_value
            
            payable = 0
            summary_lines = self.env['ssp.review.payable'].with_company(company).search([])
            for line in summary_lines:
                payable += line.total_value

            res['current_stock_value'] += round( stock,2)
            res['cash_in_hand'] += round(cash_in_hand,2)
            res['cash_at_bank'] += round(cash_at_bank,2)
            res['receivable'] += round(receivable,2)
            res['payable'] += round(payable,2)
        
        return res
    
    def get_graph_data(self, company_id=False):
        start_date, end_date = self.get_time_range()
        last_end_date = start_date - relativedelta(days=1)
        company_list = self.get_company_list(company_id)
        if self.periodicity == 'daily':
            last_start_date = last_end_date
        elif self.periodicity == 'weekly':
            last_start_date = last_end_date - relativedelta(weeks=1)
        elif self.periodicity == 'monthly':
            last_start_date = last_end_date - relativedelta(months=1)
        # Company Value asset
        assets_group = ["asset_fixed","asset_non_current","asset_cash","liability_credit_card","asset_current","asset_receivable","asset_prepayments"]
        last_added_value = 0
        for company in company_list:
            last_datas = self.env['account.move.line'].with_company(company).search([('company_id','=',company),('account_id.account_type','in',assets_group),('date','<=',last_end_date)], order='date')
            for item in last_datas:
                if item.move_id.state == "posted":
                    last_added_value += (item.debit - item.credit)
        latest_added_value = 0
        for company in company_list:
            latest_datas = self.env['account.move.line'].with_company(company).search([('company_id','=',company),('account_id.account_type','in',assets_group),('date','<=',end_date)], order='date')
            for item in latest_datas:
                if item.move_id.state == "posted":
                    latest_added_value += (item.debit - item.credit)
        img = 'red-down-arrow.png'
        if (latest_added_value - last_added_value) >= 0:
            img = 'green-up-arrow.png'
        return {
            'value': round(latest_added_value - last_added_value,2),
            'img': img
        }

    def get_domain_info(self):
        res = {}
        start_date, end_date = self.get_time_range()
        res['start_date'] = start_date
        res['end_date'] = end_date
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        res['base_url'] = base_url
        date_str = fields.Date.from_string(self.next_run_date)
        date_str = date_str.strftime('%B %d, %Y')
        res['date'] = date_str
        res['menu'] = self.get_menu_info()
        return res

    def get_menu_info(self):
        if self.periodicity == 'daily':
            menu_id = self.env.ref('management_review.ssp_reveiw_daily_menu').id,
        if self.periodicity == 'weekly':
            menu_id = self.env.ref('management_review.ssp_reveiw_week_menu').id,
        if self.periodicity == 'monthly':
            menu_id = self.env.ref('management_review.ssp_reveiw_month_menu').id,
        
        return menu_id[0]


    def get_time_range(self):
        end_date = self.next_run_date
        if self.periodicity == 'daily':
            start_date = end_date
        elif self.periodicity == 'weekly':
            start_date = end_date - relativedelta(weeks=1)
        elif self.periodicity == 'monthly':
            start_date = end_date - relativedelta(months=1)
        elif self.periodicity == 'quarterly':
            start_date = end_date - relativedelta(months=3)
        return [start_date, end_date]

    def _get_next_run_date(self):
        self.ensure_one()
        if self.periodicity == 'daily':
            delta = relativedelta(days=1)
        elif self.periodicity == 'weekly':
            delta = relativedelta(weeks=1)
        elif self.periodicity == 'monthly':
            delta = relativedelta(months=1)
        elif self.periodicity == 'quarterly':
            delta = relativedelta(months=3)
        return date.today() + delta

    def _compute_timeframes(self, company):
        now = datetime.utcnow()
        tz_name = company.resource_calendar_id.tz
        if tz_name:
            now = pytz.timezone(tz_name).localize(now)
        start_date = now.date()
        return {
            'yesterday': (
                (start_date + relativedelta(days=-1), start_date),
                (start_date + relativedelta(days=-2), start_date + relativedelta(days=-1))),
            'lastweek': (
                (start_date + relativedelta(weeks=-1), start_date),
                (start_date + relativedelta(weeks=-2), start_date + relativedelta(weeks=-1))),
            'lastmonth': (
                (start_date + relativedelta(months=-1), start_date),
                (start_date + relativedelta(months=-2), start_date + relativedelta(months=-1))),
        }

    def _get_margin_value(self, value, previous_value=0.0):
        margin = 0.0
        if (value != previous_value) and (value != 0.0 and previous_value != 0.0):
            margin = float_round((float(value-previous_value) / previous_value or 1) * 100, precision_digits=2)
        return margin

    def _format_currency_amount(self, amount, currency_id):
        pre = currency_id.position == 'before'
        symbol = u'{symbol}'.format(symbol=currency_id.symbol or '')
        return u'{pre}{0}{post}'.format(amount, pre=symbol if pre else '', post=symbol if not pre else '')

    def _format_human_readable_amount(self, amount, suffix=''):
        for unit in ['', 'K', 'M', 'G']:
            if abs(amount) < 1000.0:
                return "%3.2f%s%s" % (amount, unit, suffix)
            amount /= 1000.0
        return "%.2f%s%s" % (amount, 'T', suffix)

    @api.model
    def _cron_send_ssp_review_email(self):
        ssp_review = self.search([('next_run_date', '=', fields.Date.today()), ('state', '=', 'activated')])
        for ssp in ssp_review:
            try:
                dashboard = self.env['ssp.review.dashboard'].search([],limit=1)
                dashboard.with_context(before_mail=True).generate_summary_data()
                ssp.action_send()
            except MailDeliveryException as e:
                _logger.warning('MailDeliveryException while sending digest %d. Digest is now scheduled for next cron update.')

