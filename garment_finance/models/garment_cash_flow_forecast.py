# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Cash Flow Forecasting (SRS section 31-32, Module 20 "Cash Flow Management
System" / "Cash Flow Forecasting"; section 18, Module 37 "Cash Flow
Management"), plus AI Cash Flow Prediction (SRS section 45, Module 20 /
section 52, Module 37).

This is forward-looking (predicts a future shortfall from receivables and
payments already due in a period) and is therefore distinct from the
historical Cash Flow *Statement* (Operating/Investing/Financing
activities), which — like the rest of statutory financial reporting —
stays with the standard Odoo Accounting app per this module's scope
decision (see __manifest__.py).
"""
from odoo import api, fields, models, _


class GarmentCashFlowForecast(models.Model):
    _name = 'garment.cash.flow.forecast'
    _description = 'Garment Cash Flow Forecast'
    _inherit = ['mail.thread']
    _order = 'period_start desc'

    name = fields.Char(string='Forecast Name', required=True, default=lambda s: _('New Forecast'))
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], string='Status',
                              default='draft', tracking=True)

    opening_balance = fields.Monetary(string='Opening Balance (Current Bank Balances)',
                                       compute='_compute_forecast', store=True, currency_field='currency_id')
    expected_inflow = fields.Monetary(string='Expected Cash Inflow', compute='_compute_forecast', store=True,
                                       currency_field='currency_id',
                                       help='Outstanding Buyer Receivables due within the period.')
    expected_outflow = fields.Monetary(string='Expected Cash Outflow', compute='_compute_forecast', store=True,
                                        currency_field='currency_id',
                                        help='Outstanding Vendor Payments due, plus pending/approved Expenses, '
                                             'within the period.')
    net_cash = fields.Monetary(string='Net Cash', compute='_compute_forecast', store=True,
                                currency_field='currency_id')
    closing_balance = fields.Monetary(string='Projected Closing Balance', compute='_compute_forecast', store=True,
                                       currency_field='currency_id')

    ai_cash_flow_risk_note = fields.Text(string='AI Cash Flow Risk', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    @api.depends('period_start', 'period_end')
    def _compute_forecast(self):
        for rec in self:
            if not (rec.period_start and rec.period_end):
                rec.update({'opening_balance': 0.0, 'expected_inflow': 0.0, 'expected_outflow': 0.0,
                             'net_cash': 0.0, 'closing_balance': 0.0})
                continue

            BankAccount = self.env['garment.bank.account']
            Receivable = self.env['garment.receivable']
            Payment = self.env['garment.payment']
            Expense = self.env['garment.expense']

            opening = sum(BankAccount.search([]).mapped('current_balance'))

            due_receivables = Receivable.search([
                ('status', '!=', 'received'),
                ('due_date', '>=', rec.period_start), ('due_date', '<=', rec.period_end)])
            inflow = sum(due_receivables.mapped('outstanding_amount'))

            due_payments = Payment.search([
                ('payment_status', '!=', 'paid'),
                ('due_date', '>=', rec.period_start), ('due_date', '<=', rec.period_end)])
            due_expenses = Expense.search([
                ('status', 'in', ('approved', 'pending')),
                ('expense_date', '>=', rec.period_start), ('expense_date', '<=', rec.period_end)])
            outflow = sum(due_payments.mapped('outstanding_amount')) + sum(due_expenses.mapped('amount'))

            rec.opening_balance = opening
            rec.expected_inflow = inflow
            rec.expected_outflow = outflow
            rec.net_cash = inflow - outflow
            rec.closing_balance = opening + rec.net_cash

    def action_recompute(self):
        for rec in self:
            rec._compute_forecast()

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_run_ai_analysis(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            note = ai_engine.predict_cash_flow_risk(rec)
            rec.write({'ai_cash_flow_risk_note': note, 'ai_last_run': fields.Datetime.now()})
        return True
