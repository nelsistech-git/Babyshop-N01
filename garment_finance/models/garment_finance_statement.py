# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Financial Statement Management / Finance Executive Dashboard (SRS section
41-42 & 46-47, Module 37; section 6, 41, 46-47, Module 20).

IMPORTANT SCOPE NOTE (see __manifest__.py "DELIBERATE SCOPE DECISION"):
this is NOT a replacement for Odoo Accounting's audited General Ledger,
Trial Balance, statutory Balance Sheet or Profit & Loss Report — those
stay owned by the standard 'account' module. garment.finance.statement is
a lightweight, point-in-time snapshot built ONLY from this module's own
operational data (receivables, expenses, payments, bank balances,
budgets) so Finance/Management get the Executive Dashboard / simplified
P&L view the SRS calls for without this module re-implementing
double-entry bookkeeping.
"""
from odoo import api, fields, models, _


class GarmentFinanceStatement(models.Model):
    _name = 'garment.finance.statement'
    _description = 'Garment Finance Executive Statement (Snapshot)'
    _inherit = ['mail.thread']
    _order = 'period_end desc'

    name = fields.Char(string='Statement Name', required=True, default=lambda s: _('New Statement'))
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    state = fields.Selection([('draft', 'Draft'), ('generated', 'Generated')], string='Status',
                              default='draft', tracking=True)

    # Profit & Loss (simplified — Revenue/Cost sourced from this module's
    # own Buyer Receivable and approved Expense records for the period)
    total_revenue = fields.Monetary(string='Total Revenue', compute='_compute_statement', store=True,
                                     currency_field='currency_id')
    total_production_cost = fields.Monetary(string='Production / Operating Cost', compute='_compute_statement',
                                             store=True, currency_field='currency_id')
    gross_profit = fields.Monetary(string='Gross Profit', compute='_compute_statement', store=True,
                                    currency_field='currency_id')
    net_profit = fields.Monetary(string='Net Profit', compute='_compute_statement', store=True,
                                  currency_field='currency_id')
    gross_margin_pct = fields.Float(string='Gross Margin %', compute='_compute_statement', store=True)
    net_margin_pct = fields.Float(string='Net Margin %', compute='_compute_statement', store=True)

    # Balance-sheet-style position snapshot (not a statutory Balance Sheet)
    cash_bank_balance = fields.Monetary(string='Cash & Bank Balance', compute='_compute_statement', store=True,
                                         currency_field='currency_id')
    total_receivable = fields.Monetary(string='Accounts Receivable', compute='_compute_statement', store=True,
                                        currency_field='currency_id')
    total_payable = fields.Monetary(string='Accounts Payable', compute='_compute_statement', store=True,
                                     currency_field='currency_id')
    working_capital = fields.Monetary(string='Working Capital', compute='_compute_statement', store=True,
                                       currency_field='currency_id')

    # Budget Status (SRS section 6, "Budget Status" KPI)
    budget_allocated = fields.Monetary(string='Budget Allocated', compute='_compute_statement', store=True,
                                        currency_field='currency_id')
    budget_actual = fields.Monetary(string='Budget Actual', compute='_compute_statement', store=True,
                                     currency_field='currency_id')
    budget_variance_pct = fields.Float(string='Budget Variance %', compute='_compute_statement', store=True)

    def action_generate(self):
        for rec in self:
            rec._compute_statement()
            rec.state = 'generated'

    @api.depends('period_start', 'period_end')
    def _compute_statement(self):
        for rec in self:
            if not (rec.period_start and rec.period_end):
                rec.update({
                    'total_revenue': 0.0, 'total_production_cost': 0.0, 'gross_profit': 0.0, 'net_profit': 0.0,
                    'gross_margin_pct': 0.0, 'net_margin_pct': 0.0, 'cash_bank_balance': 0.0,
                    'total_receivable': 0.0, 'total_payable': 0.0, 'working_capital': 0.0,
                    'budget_allocated': 0.0, 'budget_actual': 0.0, 'budget_variance_pct': 0.0,
                })
                continue

            Receivable = self.env['garment.receivable']
            Expense = self.env['garment.expense']
            Payment = self.env['garment.payment']
            BankAccount = self.env['garment.bank.account']
            Budget = self.env['garment.budget']

            period_receivables = Receivable.search([
                ('invoice_date', '>=', rec.period_start), ('invoice_date', '<=', rec.period_end)])
            revenue = sum(period_receivables.mapped('amount'))

            period_expenses = Expense.search([
                ('status', '=', 'approved'),
                ('expense_date', '>=', rec.period_start), ('expense_date', '<=', rec.period_end)])
            cost = sum(period_expenses.mapped('amount'))

            gross_profit = revenue - cost
            rec.total_revenue = revenue
            rec.total_production_cost = cost
            rec.gross_profit = gross_profit
            # No further overhead/tax layer is modeled in this module (VAT/Tax
            # and Fixed Asset Depreciation are deliberately out of scope — see
            # module docstring) so Net Profit mirrors Gross Profit here.
            rec.net_profit = gross_profit
            rec.gross_margin_pct = (gross_profit / revenue * 100.0) if revenue else 0.0
            rec.net_margin_pct = rec.gross_margin_pct

            rec.cash_bank_balance = sum(BankAccount.search([]).mapped('current_balance'))
            rec.total_receivable = sum(Receivable.search([('status', '!=', 'received')]).mapped('outstanding_amount'))
            rec.total_payable = sum(Payment.search([('payment_status', '!=', 'paid')]).mapped('outstanding_amount'))
            rec.working_capital = rec.cash_bank_balance + rec.total_receivable - rec.total_payable

            period_budgets = Budget.search([
                ('period_start', '<=', rec.period_end), ('period_end', '>=', rec.period_start)])
            allocated = sum(period_budgets.mapped('budgeted_amount'))
            actual = sum(period_budgets.mapped('actual_amount'))
            rec.budget_allocated = allocated
            rec.budget_actual = actual
            rec.budget_variance_pct = ((actual - allocated) / allocated * 100.0) if allocated else 0.0
