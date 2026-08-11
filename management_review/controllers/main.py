# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools

MONTH = {
    1:'January',
    2:'February',
    3:'March',
    4:'April',
    5:'May',
    6:'Jun',
    7:'July',
    8:'August',
    9:'September',
    10:'October',
    11:'November',
    12:'December',
}

class SSPReviewController(Controller):

    @route('/ssp-review/<int:company_id>/<string:report_type>/<string:start_date>/<string:end_date>', type='http', website=True, auth='user')
    def ssp_review(self, company_id, report_type, start_date, end_date, **post):
        active_id = request.env['ssp.review'].browse(1)
        action = {}
        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)
        company_list = request.env['res.company'].search([('id','child_of',company_id)]).ids
        if report_type == "total-invoiced-amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Invoice Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Invoice Date',
                'Invoice Number',
                'Customer',
                'Salesman',
                'Invoice Amount'
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency'
            ]
            data_line = list()
            total_invoice_amount = 0

            for company in company_list:
                all_invoices = request.env['account.move'].with_company(company).search([('company_id','=',company),('invoice_date','>=',start_date),('invoice_date','<=',end_date),('state','in',['posted']),('move_type','=','out_invoice')])
                for invoice in all_invoices:
                    total_invoice_amount += invoice.amount_total
                    data_line.append((invoice.invoice_date, invoice.name, invoice.partner_id.name, invoice.invoice_user_id.name, invoice.amount_total))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","",total_invoice_amount]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "total-invoice-received-amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Invoice Received Amount Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Payment Date',
                'Payment Number',
                'Invoice Number',
                'Customer',
                'Invoice Amount',
                'Payment Amount'
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
                'currency',
            ]
            data_line = list()
            total_invoice_received_amount = 0

            for company in company_list:
                all_received_payments = request.env['account.payment'].with_company(company).search([('company_id','=',company),('date','<=',end_date),('date','>=',start_date),('payment_type','=','inbound'),('state','in',['posted'])])
                for payment in all_received_payments:
                    invoice_id = payment.reconciled_invoice_ids
                    if invoice_id and fields.Date.from_string(invoice_id.invoice_date) >= start_date and fields.Date.from_string(invoice_id.invoice_date) <= end_date:
                        total_invoice_received_amount += payment.amount
                        data_line.append((payment.date, payment.name, payment.ref, payment.partner_id.name, invoice_id.amount_total, payment.amount))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","","",total_invoice_received_amount]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "total-invoice-due-amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Invoice Due Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Invoice Date',
                'Invoice Number',
                'Customer',
                'Salesman',
                'Invoice Amount',
                'Invoice Due',
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
                'currency',
            ]
            data_line = list()
            total_invoice_due_amount = 0

            for company in company_list:
                all_invoices = request.env['account.move'].with_company(company).search([('company_id','=',company),('invoice_date','>=',start_date),('invoice_date','<=',end_date),('state','in',['posted']),('move_type','=','out_invoice')])
                for invoice in all_invoices:
                    if invoice.amount_residual>0:
                        total_invoice_due_amount += invoice.amount_residual
                        data_line.append((invoice.invoice_date, invoice.name, invoice.partner_id.name, invoice.invoice_user_id.name, invoice.amount_total, invoice.amount_residual))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","","",total_invoice_due_amount]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "total-due-collection-amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Invoice Due Collection Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Payment Date',
                'Payment Number',
                'Invoice Number',
                'Customer',
                'Invoiced Amount',
                'Payment Amount'
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
                'currency',
            ]
            data_line = list()
            total_due_collection_amount = 0

            for company in company_list:
                all_received_payments = request.env['account.payment'].with_company(company).search([('company_id','=',company),('date','<=',end_date),('date','>=',start_date),('payment_type','=','inbound'),('state','in',['posted'])])
                for payment in all_received_payments:
                    # invoice_id = payment.reconciled_invoice_ids
                    for invoice_id in payment.reconciled_invoice_ids:
                        payment_amount = invoice_id.amount_total - invoice_id.amount_residual
                        payment_lines = invoice_id._get_reconciled_invoices_partials()
                        for line in payment_lines:
                            # if line[2].payment_id.id == payment.id:
                            if len(line) > 2 and hasattr(line[2], 'payment_id') and line[2].payment_id.id == payment.id:
                                payment_amount = line[1]

                        if invoice_id and fields.Date.from_string(invoice_id.invoice_date) < start_date:
                            total_due_collection_amount += payment_amount
                            data_line.append((payment.date, payment.name, payment.ref, payment.partner_id.name, invoice_id.amount_total, payment_amount))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","","",total_due_collection_amount]
            print('data',data)
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "total-received-amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Received Payment Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Payment Date',
                'Payment Number',
                'Invoice Number',
                'Customer',
                'Invoiced Amount',
                'Payment Amount'
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
                'currency',
            ]
            data_line = list()
            total_received_payment_amount = 0

            for company in company_list:
                all_received_payments = request.env['account.payment'].with_company(company).search([('company_id','=',company),('date','<=',end_date),('date','>=',start_date),('payment_type','=','inbound'),('state','in',['posted'])])
                for payment in all_received_payments:
                    invoice_id = payment.reconciled_invoice_ids
                    total_received_payment_amount += payment.amount
                    data_line.append((payment.date, payment.name, payment.ref, payment.partner_id.name, invoice_id.amount_total, payment.amount))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","","",total_received_payment_amount]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "total-invoice-refund-amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Invoice Refund Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Invoice Date',
                'Invoice Number',
                'Customer',
                'Salesman',
                'Invoice Amount'
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
            ]
            data_line = list()
            total_invoice_refund_amount = 0
            for company in company_list:
                all_invoices = request.env['account.move'].with_company(company).search([('company_id','=',company),('invoice_date','>=',start_date),('invoice_date','<=',end_date),('state','in',['posted']),('move_type','=','out_refund')])
                for invoice in all_invoices:
                    total_invoice_refund_amount += invoice.amount_total
                    data_line.append((invoice.invoice_date, invoice.name, invoice.partner_id.name, invoice.invoice_user_id.name, invoice.amount_total))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","",total_invoice_refund_amount]
            return request.render('management_review.ssp_review_report_document', data)
        
    
        ######################## Purchase
        if report_type == "total-bill-amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Bill Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Bill Date',
                'Bill Number',
                'Customer',
                'Salesman',
                'Bill Amount'
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency'
            ]
            data_line = list()
            total_invoice_amount = 0

            for company in company_list:
                all_invoices = request.env['account.move'].with_company(company).search([('company_id','=',company),('invoice_date','>=',start_date),('invoice_date','<=',end_date),('state','in',['posted']),('move_type','=','in_invoice')])
                for invoice in all_invoices:
                    total_invoice_amount += invoice.amount_total
                    data_line.append((invoice.invoice_date, invoice.name, invoice.partner_id.name, invoice.invoice_user_id.name, invoice.amount_total))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","",total_invoice_amount]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "total-bill-paid-amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Bill Payments Amount Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Payment Date',
                'Payment Number',
                'Bill Number',
                'Customer',
                'Bill Amount',
                'Payment Amount'
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
                'currency',
            ]
            data_line = list()
            total_invoice_received_amount = 0
            for company in company_list:
                all_received_payments = request.env['account.payment'].with_company(company).search([('company_id','=',company),('date','<=',end_date),('date','>=',start_date),('payment_type','=','outbound'),('state','in',['posted'])])
                for payment in all_received_payments:
                    invoice_id = payment.reconciled_bill_ids
                    if invoice_id and fields.Date.from_string(invoice_id.invoice_date) >= start_date and fields.Date.from_string(invoice_id.invoice_date) <= end_date:
                        total_invoice_received_amount += payment.amount
                        data_line.append((payment.date, payment.name, payment.ref, payment.partner_id.name, invoice_id.amount_total, payment.amount))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","","",total_invoice_received_amount]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "total-bill-due_amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Bill Due Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Bill Date',
                'Bill Number',
                'Customer',
                'Salesman',
                'Bill Amount',
                'Bill Due',
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
                'currency',
            ]
            data_line = list()
            total_invoice_due_amount = 0
            for company in company_list:
                all_invoices = request.env['account.move'].with_company(company).search([('company_id','=',company),('invoice_date','>=',start_date),('invoice_date','<=',end_date),('state','in',['posted']),('move_type','=','in_invoice')])
                for invoice in all_invoices:
                    if invoice.amount_residual>0:
                        total_invoice_due_amount += invoice.amount_residual
                        data_line.append((invoice.invoice_date, invoice.name, invoice.partner_id.name, invoice.invoice_user_id.name, invoice.amount_total, invoice.amount_residual))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","","",total_invoice_due_amount]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "total-due-paid-amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Bill Due Payment Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Payment Date',
                'Payment Number',
                'Bill Number',
                'Customer',
                'Bill Amount',
                'Payment Amount'
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
                'currency',
            ]
            data_line = list()
            total_due_collection_amount = 0
            for company in company_list:
                all_received_payments = request.env['account.payment'].with_company(company).search([('company_id','=',company),('date','<=',end_date),('date','>=',start_date),('payment_type','=','outbound'),('state','in',['posted'])])
                for payment in all_received_payments:
                    # invoice_id = payment.reconciled_bill_ids
                    for invoice_id in payment.reconciled_bill_ids:
                        payment_amount = invoice_id.amount_total - invoice_id.amount_residual
                        payment_lines = invoice_id._get_reconciled_invoices_partials()
                        for line in payment_lines:
                            if len(line) > 2 and hasattr(line[2], 'payment_id') and line[2].payment_id.id == payment.id:
                                payment_amount = line[1]

                        if invoice_id and fields.Date.from_string(invoice_id.invoice_date) < start_date:
                            total_due_collection_amount += payment_amount
                            data_line.append((payment.date, payment.name, payment.ref, payment.partner_id.name, invoice_id.amount_total, payment_amount))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","","",total_due_collection_amount]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "total-payment-amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Payment Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Payment Date',
                'Payment Number',
                'Bill Number',
                'Customer',
                'Bill Amount',
                'Payment Amount'
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
                'currency',
            ]
            data_line = list()
            total_received_payment_amount = 0
            for company in company_list:
                all_received_payments = request.env['account.payment'].with_company(company).search([('company_id','=',company),('date','<=',end_date),('date','>=',start_date),('payment_type','=','outbound'),('state','in',['posted'])])
                for payment in all_received_payments:
                    invoice_id = payment.reconciled_bill_ids
                    total_received_payment_amount += payment.amount
                    data_line.append((payment.date, payment.name, payment.ref, payment.partner_id.name, invoice_id.amount_total, payment.amount))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","","",total_received_payment_amount]
            return request.render('management_review.ssp_review_report_document', data)

        
        if report_type == "total-bill-refund-amount":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Bill Refund Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Bill Date',
                'Bill Number',
                'Customer',
                'Salesman',
                'Bill Amount'
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency'
            ]
            data_line = list()
            total_bill_refund_amount = 0
            for company in company_list:
                all_invoices = request.env['account.move'].with_company(company).search([('company_id','=',company),('invoice_date','<=',end_date),('invoice_date','>=',start_date),('state','in',['posted']),('move_type','=','in_refund')])
                for invoice in all_invoices:
                    total_bill_refund_amount += invoice.amount_total
                    data_line.append((invoice.invoice_date, invoice.name, invoice.partner_id.name, invoice.invoice_user_id.name, invoice.amount_total))
            data['data_line'] = data_line
            data['footer'] = ["Total","","","",total_bill_refund_amount]
            return request.render('management_review.ssp_review_report_document', data)
        
        ########################## Stock

        if report_type == "current-stock-value":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Current Stock Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Product-Ref',
                'Value',
            ]
            data['col_type'] = [
                'text',
                'currency',
            ]
            data_line = list()
            current_stock_value = 0
            for company in company_list:
                valuation_accounts = request.env['product.category'].with_company(company).search([]).mapped('property_stock_valuation_account_id').ids
                account_ids = valuation_accounts
                # _logger.info(account_ids)
                if len(account_ids) == 1:
                    query = "SELECT move_line.name as label,move_line.product_id as product_id, move_line.debit as debit, move_line.credit as credit FROM account_move_line move_line JOIN account_move move ON move.id = move_line.move_id WHERE move.state='posted' and move_line.account_id = {} and move.company_id = {};".format(str(account_ids[0]),str(company))
                else:
                    query = "SELECT move_line.name as label,move_line.product_id as product_id, move_line.debit as debit, move_line.credit as credit FROM account_move_line move_line JOIN account_move move ON move.id = move_line.move_id WHERE move.state='posted' and move_line.account_id in {} and move.company_id = {};".format(str(tuple(account_ids)),str(company))
                # _logger.info(query)
                request.env.cr.execute(query)
                csv_datas = request.env.cr.dictfetchall()
                # _logger.info(csv_datas)
                value = 0
                for item in csv_datas:
                    # product = request.env['product.product'].browse(item['product_id'])
                    value = item['debit'] - item['credit']
                    current_stock_value += value
                    data_line.append((item['label'], '%.2f' % value))
                # all_product_ids = request.env['product.product'].with_company(company).search([('company_id','=',company),('type','=','product'),('qty_available','!=',0)])
                # for product_id in all_product_ids:
                #     product_move_line_ids = request.env['stock.valuation.layer'].with_company(company).search([('company_id','=',company),('product_id','=',product_id.id)])
                    
                #     value = 0
                #     qty = 0
                #     for move_line in product_move_line_ids:
                #         qty = qty + move_line.quantity
                #         value = value + move_line.value
                #     current_stock_value += value
                #     data_line.append((product_id.name, qty, '%.2f' % value))
            data['data_line'] = data_line
            data['footer'] = ["Total", '%.2f' % current_stock_value]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "cost-of-good-sold":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Cost Of Good Sold Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Product',
                'Value',
            ]
            data['col_type'] = [
                'text',
                'currency',
            ]
            data_line = list()
            cost_of_good_sold = 0
            for company in company_list:
                account_type = request.env['account.account.tag'].search([['name','=','Cost of Revenue']]).id
                account_ids = request.env['account.account'].with_company(company).search([('company_id','=',company),['account_type','=',account_type]]).ids
                all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),['account_id','in',account_ids],['date','>=',start_date],['date','<=',end_date]])
                
                for item in all_filtered_journal_items:
                    cost_of_good_sold += (item.debit - item.credit)
                    data_line.append((item.product_id.name, (item.debit - item.credit)))
            
            data['data_line'] = data_line
            data['footer'] = ["Total",cost_of_good_sold]
            return request.render('management_review.ssp_review_report_document', data)
            
        ###################### Account Balance
        if report_type == "cash-in-hand":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Cash In Hand"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Date',
                'Number',
                'Customer',
                'Reference',
                'Value',
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
            ]
            data_line = list()
            for company in company_list:
                all_journals = request.env['account.journal'].with_company(company).search([('company_id','=',company),('type','=','cash')])
                for journal in all_journals:
                    cash_accounts = list()
                    cash_accounts.append(journal.default_account_id.id)
                    # cash_accounts.append(journal.payment_debit_account_id.id)
                    # cash_accounts.append(journal.payment_credit_account_id.id)
                    cash_in_hand = 0
                    all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),('account_id','in',cash_accounts),('move_id.state','=','posted'),['date','<',start_date]])
                    for item in all_filtered_journal_items: 
                        cash_in_hand += (item.debit - item.credit)
                    opening_balance = cash_in_hand
                    all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),('account_id','in',cash_accounts),('move_id.state','=','posted'),['date','>=',start_date],['date','<=',end_date]])
                    if opening_balance != 0 or len(all_filtered_journal_items)>0:
                        data_line.append(("",str("ACCOUNT - "+journal.default_account_id.code + " " + journal.default_account_id.name),"","",""))
                        data_line.append(("Opening Balance","","","",'%.2f' % opening_balance))
                    for item in all_filtered_journal_items:
                        cash_in_hand += (item.debit - item.credit)
                        data_line.append((item.date, item.move_id.name, item.partner_id.name, item.ref, '%.2f' % (item.debit - item.credit)))
                    if opening_balance != 0 or len(all_filtered_journal_items)>0:
                        data_line.append(["Total","","","",'%.2f' % cash_in_hand])

                # for journal in all_journals:
                #     cash_accounts = list()
                #     cash_accounts.append(journal.default_account_id.id)
                #     cash_in_hand = 0
                #     all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([
                #         ('company_id', '=', company),
                #         ('account_id', 'in', cash_accounts),
                #         ('move_id.state', '=', 'posted'),
                #         ['date', '<', start_date]
                #     ])
                #     for item in all_filtered_journal_items:
                #         cash_in_hand += (item.debit - item.credit)
                #     opening_balance = cash_in_hand
                #     all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([
                #         ('company_id', '=', company),
                #         ('account_id', 'in', cash_accounts),
                #         ('move_id.state', '=', 'posted'),
                #         ['date', '>=', start_date],
                #         ['date', '<=', end_date]
                #     ])
                #     if opening_balance != 0 or len(all_filtered_journal_items) > 0:
                #         data_line.append(("", str("ACCOUNT - " + journal.default_account_id.code + " " + journal.default_account_id.name), "", "", ""))
                #         data_line.append(("Opening Balance", "", "", '', '%.2f' % opening_balance))
                #     for item in all_filtered_journal_items:
                #         cash_in_hand += (item.debit - item.credit)
                #         data_line.append((item.date, item.move_id.name, item.partner_id.name, item.ref, '%.2f' % (item.debit - item.credit)))
                #     if opening_balance != 0 or len(all_filtered_journal_items) > 0:
                #         data_line.append(["Total", "", "", "", '%.2f' % cash_in_hand])
            data['data_line'] = data_line
            # data['footer'] = ["Total","","","",cash_in_hand]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "cash-at-bank":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Cash At Bank"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Date',
                'Number',
                'Customer',
                'Reference',
                'Value',
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
            ]
            data_line = list()
            for company in company_list:
                all_journals = request.env['account.journal'].with_company(company).search([('company_id','=',company),('type','=','bank')])
                for journal in all_journals:
                    bank_accounts = list()
                    bank_accounts.append(journal.default_account_id.id)
                    # bank_accounts.append(journal.payment_debit_account_id.id)
                    # bank_accounts.append(journal.payment_credit_account_id.id)
                    cash_at_bank = 0
                    all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),('account_id','in',bank_accounts),('move_id.state','=','posted'),['date','<',start_date]])
                    for item in all_filtered_journal_items: 
                        cash_at_bank += (item.debit - item.credit)
                    opening_balance = cash_at_bank
                    # data_line.append(("",str("ACCOUNT - "+account.code + " " + account.name),"","",""))
                    # data_line.append(("Opening Balance","","","",opening_balance))
                    all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),('account_id','in',bank_accounts),('move_id.state','=','posted'),['date','>=',start_date],['date','<=',end_date]])
                    if opening_balance > 0 or len(all_filtered_journal_items)>0:
                        data_line.append(("",str("ACCOUNT - "+journal.default_account_id.code + " " + journal.default_account_id.name),"","",""))
                        data_line.append(("Opening Balance","","","",'%.2f' % opening_balance))
                    for item in all_filtered_journal_items:
                        cash_at_bank += (item.debit - item.credit)
                        data_line.append((item.date, item.move_id.name, item.partner_id.name, item.ref, (item.debit - item.credit)))
                    if opening_balance > 0 or len(all_filtered_journal_items)>0:
                        data_line.append(["Total","","","",'%.2f' % cash_at_bank])
            data['data_line'] = data_line
            # data['footer'] = ["Total","","","",cash_at_bank]
            return request.render('management_review.ssp_review_report_document', data)


        if report_type == "revenue":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Revenue"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Reference',
                'Value',
            ]
            data['col_type'] = [
                'text',
                'currency',
            ]
            data_line = list()
            total_inc = 0
            total_cor = 0
            total_exp = 0
            gross_profit = 0
            net_profit = 0

            for company in company_list:
                ######## Account Income 
                account_type = request.env['account.account.tag'].search([['name','=','Income']]).id
                account_ids = request.env['account.account'].with_company(company).search([('company_id','=',company),['account_type','=',account_type]]).ids
                ac_ids = account_ids
                account_type = request.env['account.account.tag'].search([['name','=','Other Income']]).id
                account_ids = request.env['account.account'].with_company(company).search([('company_id','=',company),['account_type','=',account_type]]).ids
                ac_ids = ac_ids + account_ids
                all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),['account_id','in',ac_ids],['date','>=',start_date],['date','<=',end_date]])
                
                for item in all_filtered_journal_items:
                    if item.move_id.state == "posted":
                        total_inc += (item.credit - item.debit)
                
            for company in company_list:
                ######## Account Cost of Revenue
                account_type = request.env['account.account.tag'].search([['name','=','Cost of Revenue']]).id
                account_ids = request.env['account.account'].with_company(company).search([('company_id','=',company),['account_type','=',account_type]]).ids
                all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),['account_id','in',account_ids],['date','>=',start_date],['date','<=',end_date]])
                
                for item in all_filtered_journal_items:
                    if item.move_id.state == "posted":
                        total_cor += (item.debit - item.credit)
                
            #Gross Profit
            gross_profit = (total_inc - total_cor)
            
            
            for company in company_list:
                ######## Account Expense
                account_type = request.env['account.account.tag'].search([['name','=','Expenses']]).id
                account_ids = request.env['account.account'].with_company(company).search([('company_id','=',company),['account_type','=',account_type]]).ids
                ac_ids = account_ids
                account_type = request.env['account.account.tag'].search([['name','=','Depreciation']]).id
                account_ids = request.env['account.account'].with_company(company).search([('company_id','=',company),['account_type','=',account_type]]).ids
                ac_ids = ac_ids + account_ids
                all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),['account_id','in',ac_ids],['date','>=',start_date],['date','<=',end_date]])
                
                for item in all_filtered_journal_items:
                    if item.move_id.state == "posted":
                        total_exp += (item.debit - item.credit)

            #Net Profit
            net_profit = (gross_profit - total_exp)
            
            data_line.append(('Total Income', '%.2f' % total_inc))
            data_line.append(('Total Cost of Good Sold', '%.2f' % total_cor))
            data_line.append(('Total Gross Profit', '%.2f' % gross_profit))
            data_line.append(('Total Expense', '%.2f' % total_exp))
            data_line.append(('Total Revenue', '%.2f' % net_profit))
            data['data_line'] = data_line
            # data['footer'] = ["Total","","","",cash_at_bank]
            return request.render('management_review.ssp_review_report_document', data)
            

        if report_type == "income":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Income Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Date',
                'Number',
                'Customer',
                'Reference',
                'Value',
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
            ]
            data_line = list()
            income = 0
            for company in company_list:
                all_bc_account = request.env['account.account'].with_company(company).search([('company_id','=',company),('account_type','in',["income", "income_other"])])
                for account in all_bc_account:
                    all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),('account_id','=',account.id),['date','>=',start_date],['date','<=',end_date]])
                    for item in all_filtered_journal_items:
                        if item.move_id.state == "posted":
                            income += (item.credit - item.debit)
                            data_line.append((item.date, item.move_id.name, item.partner_id.name, item.ref, (item.credit - item.debit)))
            
            data_line.append(["Total","","","",'%.2f' % income])
            data['data_line'] = data_line
            # data['footer'] = ["Total","","","",cash_at_bank]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "expense":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Expense Report"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Date',
                'Number',
                'Customer',
                'Reference',
                'Value',
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
            ]
            data_line = list()
            income = 0
            for company in company_list:
                all_bc_account = request.env['account.account'].with_company(company).search([('company_id','=',company),('account_type','in',["expense", "expense_depreciation"])])
                for account in all_bc_account:
                    all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),('account_id','=',account.id),['date','>=',start_date],['date','<=',end_date]])
                    for item in all_filtered_journal_items:
                        if item.move_id.state == "posted":
                            income += (item.credit - item.debit)
                            data_line.append((item.date, item.move_id.name, item.partner_id.name, item.ref, (item.credit - item.debit)))
            
            data_line.append(["Total","","","",'%.2f' % income])
            data['data_line'] = data_line
            # data['footer'] = ["Total","","","",cash_at_bank]
            return request.render('management_review.ssp_review_report_document', data)
        
        if report_type == "payable":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Outstanding Payable"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Date',
                'Number',
                'Customer',
                'Reference',
                'Value',
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
            ]
            data_line = list()
            payable = 0
            for company in company_list:
                all_payable_account = request.env['account.account'].with_company(company).search([('company_id','=',company),('account_type','in',["liability_payable"])])
                for account in all_payable_account:
                    all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),('account_id','=',account.id)])
                    for item in all_filtered_journal_items:
                        if item.move_id.state == "posted":
                            payable += (item.credit - item.debit)
                            data_line.append((item.date, item.move_id.name, item.partner_id.name, item.ref, (item.credit - item.debit)))
            
            data_line.append(["Total","","","",'%.2f' % payable])
            data['data_line'] = data_line
            # data['footer'] = ["Total","","","",cash_at_bank]
            return request.render('management_review.ssp_review_report_document', data)

        if report_type == "receivable":
            data = dict()
            data['user'] = request.env.user
            data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
            data['report_header'] = "Outstanding Receivable"
            data['start_date'] = start_date
            data['end_date'] = end_date
            data['table_header'] = [
                'Date',
                'Number',
                'Customer',
                'Reference',
                'Value',
            ]
            data['col_type'] = [
                'text',
                'text',
                'text',
                'text',
                'currency',
            ]
            data_line = list()
            receivable = 0
            for company in company_list:
                print('company',company)
                all_receivable_account = request.env['account.account'].with_company(company).search([('company_id','=',company),('account_type','in',["asset_receivable"])])
                print('all_receivable_account',all_receivable_account)
                for account in all_receivable_account:
                    all_filtered_journal_items = request.env['account.move.line'].with_company(company).search([('company_id','=',company),('account_id','=',account.id)])
                    for item in all_filtered_journal_items:
                        if item.move_id.state == "posted":
                            receivable += (item.debit - item.credit)
                            data_line.append((item.date, item.move_id.name, item.partner_id.name, item.ref, (item.debit - item.credit)))
            
            data_line.append(["Total","","","",'%.2f' % receivable])
            data['data_line'] = data_line
            # data['footer'] = ["Total","","","",cash_at_bank]
            return request.render('management_review.ssp_review_report_document', data)


    @route('/comparison/report/<int:company_id>/<string:report_type>/<string:current_date>/<int:month>', type='http', website=True, auth='user')
    def ssp_review_comparison(self, company_id, report_type, current_date, month, **post):
        data = dict()
        data['user'] = request.env.user
        data['context_timestamp'] = lambda t: fields.Datetime.context_timestamp(request.env.user, t)
        current_date = fields.Date.from_string(current_date)
        current_month_start = fields.Date.from_string(str(current_date.year)+"-"+str(current_date.month)+"-1")
        year_start_date = current_month_start- relativedelta(months=month-1)
        data['report_header'] = "Company Summary Report for the "+MONTH[year_start_date.month]+" "+str(year_start_date.year)+" to "+MONTH[current_date.month]+" "+str(current_date.year)+" ( "+str(month)+" Months )"
        data['start_date'] = year_start_date
        data['end_date'] = current_date
        data['table_header'] = ['Particular']
        data['col_type'] = ['text']
        data['data_line'] = list()
        header = True
        all_category = request.env['comparison.report.category'].search([],order='sequence')    
        collection_category = request.env.ref('management_review.comparison_category_4')
        for category in all_category:
            domain = [('move_id.state','=','posted'),('company_id','=',company_id)]
            if category.config_type == 'account':
                domain.append(('account_id','in',category.account_ids.ids))
            else:
                domain.append(('account_id.account_type','in',category.account_type.ids))
            yearly_total = 0
            iteration = 1
            start_date = year_start_date
            dataline = [category.name]
            while start_date < current_date:
                month_start_date = start_date
                start_date = month_start_date + relativedelta(months=1)
                month_end_date = start_date - relativedelta(days=1)
                if header:
                    data['table_header'].append(MONTH[month_start_date.month])
                    data['col_type'].append('number')
                if category.account_type == 'pl':
                    value = self.get_profit_loss(company_id, month_start_date, month_end_date)
                else:
                    if category.calculation == 'cumulative' and iteration == 1:
                        journal_domain = domain + [('date','<=',month_end_date)]
                        iteration += 1
                    else:
                        journal_domain = domain + [('date','>=',month_start_date),('date','<=',month_end_date)]
                    all_journal_items = request.env['account.move.line'].search(journal_domain)
                    total = 0
                    for item in all_journal_items:
                        if category.account_type in ['asset','expense']:
                            balance = item.debit - item.credit
                        else:
                            balance = item.credit - item.debit
                        if collection_category.id == category.id:
                            if not item.move_id.is_collection:
                                continue
                        if (category.entry_type == 'in' and balance > 0) or (category.entry_type == 'out' and balance < 0) or category.entry_type == 'both':
                            total += balance
                    value = total
                    if category.calculation == 'cumulative':
                        yearly_total += total
                        value = yearly_total
                dataline.append(round(value,2))
            data['data_line'].append(dataline)    
            header = False    
        
        ### Number of Employee
        start_date = year_start_date
        manpower_dataline = ["Total Manpower"]
        territory_dataline = ["Total Territory"]
        product_dataline = ["Total Product"]
        fleet_dataline = ["Fleet"]
        while start_date < current_date:
            month_start_date = start_date
            start_date = month_start_date + relativedelta(months=1)
            month_end_date = start_date - relativedelta(days=1)
            employee_count = request.env['hr.employee'].search_count([('create_date','<=',month_end_date)])
            manpower_dataline.append(employee_count)
            territory_count = request.env['territory.territory'].search_count([('create_date','<=',month_end_date)])
            territory_dataline.append(territory_count)
            product_count = request.env['product.product'].search_count([('type','=','product'),('create_date','<=',month_end_date)])
            product_dataline.append(product_count)
            fleet_count = request.env['fleet.vehicle'].search_count([('create_date','<=',month_end_date)])
            fleet_dataline.append(fleet_count)
        data['data_line'].append(manpower_dataline)  
        data['data_line'].append(territory_dataline)  
        data['data_line'].append(product_dataline)  
        data['data_line'].append(fleet_dataline)  
        return request.render('management_review.ssp_review_report_document_comparision', data)

    def get_profit_loss(self, company_id, from_date, to_date):
        journal_state = ['posted',]
        total_inc = 0
        total_cor = 0
        total_exp = 0
        gross_profit = 0
        net_profit = 0

        ######## Account Income 
        account_type = request.env['account.account.tag'].search([['name','=','Income']]).id
        account_ids = request.env['account.account'].search([['account_type','=',account_type],['company_id','child_of',company_id]]).ids
        all_filtered_journal_items = request.env['account.move.line'].search([['account_id','in',account_ids],['date','>=',from_date],['date','<=',to_date]])
        
        for item in all_filtered_journal_items:
            if item.move_id.state in journal_state:
                total_inc += (item.credit - item.debit)
        
        ######## Account Other Income 
        account_type = request.env['account.account.tag'].search([['name','=','Other Income']]).id
        account_ids = request.env['account.account'].search([['account_type','=',account_type],['company_id','child_of',company_id]]).ids
        all_filtered_journal_items = request.env['account.move.line'].search([['account_id','in',account_ids],['date','>=',from_date],['date','<=',to_date]])
        
        for item in all_filtered_journal_items:
            if item.move_id.state in journal_state:
                total_inc += (item.credit - item.debit)
        
        ######## Account Cost of Revenue
        account_type = request.env['account.account.tag'].search([['name','=','Cost of Revenue']]).id
        account_ids = request.env['account.account'].search([['account_type','=',account_type],['company_id','child_of',company_id]]).ids
        all_filtered_journal_items = request.env['account.move.line'].search([['account_id','in',account_ids],['date','>=',from_date],['date','<=',to_date]])
        
        for item in all_filtered_journal_items:
            if item.move_id.state in journal_state:
                total_cor += (item.debit - item.credit)
        
        #Gross Profit
        gross_profit = (total_inc - total_cor)
        
        ######## Account Expense
        account_type = request.env['account.account.tag'].search([['name','=','Expenses']]).id
        account_ids = request.env['account.account'].search([['account_type','=',account_type],['company_id','child_of',company_id]]).ids
        all_filtered_journal_items = request.env['account.move.line'].search([['account_id','in',account_ids],['date','>=',from_date],['date','<=',to_date]])
        
        for item in all_filtered_journal_items:
            if item.move_id.state in journal_state:
                total_exp += (item.debit - item.credit)
            
        
        ######## Account Depreciation
        account_type = request.env['account.account.tag'].search([['name','=','Depreciation']]).id
        account_ids = request.env['account.account'].search([['account_type','=',account_type],['company_id','child_of',company_id]]).ids
        all_filtered_journal_items = request.env['account.move.line'].search([['account_id','in',account_ids],['date','>=',from_date],['date','<=',to_date]])
        
        for item in all_filtered_journal_items:
            if item.move_id.state in journal_state:
                total_exp += (item.debit - item.credit)
        
        #Net Profit
        net_profit = (gross_profit - total_exp)
        
        return net_profit