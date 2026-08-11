# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BabyShopBankExpense(models.Model):
    """Daily Bank Expense Report - entered per showroom/branch, per day.

    Mirrors the layout of the manual 'BANK EXPENCE REPORT' sheet:
    grouped by Sale Team, one line per showroom, with income (cash/card
    sales, bank deposit) and expense (card sales adjustment, showroom
    expenses, head office) columns, ending in a closing balance.
    """
    _name = 'baby.shop.bank.expense'
    _description = 'Baby Shop - Daily Bank Expense Report Line'
    _order = 'date desc, sale_team_id, showroom_id'
    _rec_name = 'showroom_id'

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, index=True)
    sale_team_id = fields.Many2one('crm.team', string='Sale Team', required=True, index=True)

    # showroom = branch = a child company of the main "BABY SHOP LTD" company
    showroom_id = fields.Many2one(
        'res.company', string='Show Room', required=True,
        domain="[('parent_id', '!=', False)]", index=True,
    )

    # ---- Income ----
    opening_balance = fields.Monetary(string='Opening Balance', default=0.0)
    cash_sales = fields.Monetary(string='Cash Sales', default=0.0)
    card_sales_city = fields.Monetary(string='Card Sales (City)', default=0.0)
    card_sales_ucb = fields.Monetary(string='Card Sales (UCB)', default=0.0)
    total_card_sales = fields.Monetary(string='Total Card Sales', compute='_compute_totals', store=True)
    total_sales = fields.Monetary(string='Total Sales', compute='_compute_totals', store=True)
    total_sales_with_opening = fields.Monetary(
        string='Total Sales with Opening', compute='_compute_totals', store=True)

    bank_deposit = fields.Monetary(string='Bank Deposit', default=0.0)
    bank_name = fields.Char(string='Bank Name', default='DBBL Grey Fabrics')

    # ---- Expenses ----
    card_sales_expense = fields.Monetary(
        string='Card Sales', default=0.0,
        help='Card sales amount shown again on the expense side, since this'
             ' money does not come in as physical cash at the showroom.')
    showroom_expenses = fields.Monetary(string='Show Room Expenses', default=0.0)
    head_office_expenses = fields.Monetary(string='Head Office', default=0.0)
    total_expenses = fields.Monetary(string='Total Expenses', compute='_compute_totals', store=True)

    closing_balance = fields.Monetary(string='Closing Balance', compute='_compute_totals', store=True)

    today_bank_deposit = fields.Monetary(string="Today's Bank Deposit", default=0.0)
    today_bank_name = fields.Char(string='Bank Name', default='DBBL Grey Fabrics')

    net_closing = fields.Monetary(string='Net Closing', compute='_compute_totals', store=True)

    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.parent_id or self.env.company)
    note = fields.Char(string='Note')

    @api.depends('opening_balance', 'cash_sales', 'card_sales_city', 'card_sales_ucb',
                 'bank_deposit', 'card_sales_expense', 'showroom_expenses',
                 'head_office_expenses', 'today_bank_deposit')
    def _compute_totals(self):
        for rec in self:
            rec.total_card_sales = rec.card_sales_city + rec.card_sales_ucb
            rec.total_sales = rec.cash_sales + rec.total_card_sales
            rec.total_sales_with_opening = rec.opening_balance + rec.total_sales
            rec.total_expenses = rec.card_sales_expense + rec.showroom_expenses + rec.head_office_expenses
            rec.closing_balance = rec.total_sales_with_opening - rec.bank_deposit - rec.total_expenses
            rec.net_closing = rec.closing_balance - rec.today_bank_deposit
