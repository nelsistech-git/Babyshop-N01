# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BabyShopStoreReport(models.Model):
    """Daily Store Report - entered per showroom/branch, per day.

    Mirrors the 'Accounts Report / STORE REPORT / TRACK SALE & CUSTOMER /
    DAILY TARGET' layout used by store managers.
    """
    _name = 'baby.shop.store.report'
    _description = 'Baby Shop - Daily Store Report'
    _order = 'date desc, showroom_id'
    _rec_name = 'showroom_id'

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, index=True)
    showroom_id = fields.Many2one(
        'res.company', string='Show Room', required=True,
        domain="[('parent_id', '!=', False)]", index=True,
    )

    # ---- Accounts Report ----
    opening_balance = fields.Monetary(string='Opening Balance', default=0.0)
    cash_sale_city = fields.Monetary(string='Cash Sale City', default=0.0)
    card_ucb = fields.Monetary(string='Card UCB', default=0.0)
    total_card_sale = fields.Monetary(string='Total Card Sale', compute='_compute_totals', store=True)
    m_pay = fields.Monetary(string='M Pay', default=0.0)
    total_sale = fields.Monetary(string='Total Sale', compute='_compute_totals', store=True)
    cash_received = fields.Monetary(string='Cash Received', default=0.0)
    total_expense = fields.Monetary(string='Total Expanse', default=0.0)
    total_vat = fields.Monetary(string='Total Vat', default=0.0)
    closing_balance = fields.Monetary(string='Closing Balance', compute='_compute_totals', store=True)
    sale_qty = fields.Integer(string='Sale Qty', default=0)

    # ---- Track Sale & Customer ----
    stock_opening_qty = fields.Integer(string='Opening Balance (Qty)', default=0)
    received_qty = fields.Integer(string='Received Qty', default=0)
    return_qty = fields.Integer(string='Return', default=0)
    stock_sale_qty = fields.Integer(string='Sale Qty', default=0)
    closing_store_qty = fields.Integer(string='Closing Store', compute='_compute_totals', store=True)
    gm_store = fields.Char(string='GM Store')
    md_store = fields.Char(string='MD Store')

    oven_sale_amount = fields.Monetary(string='Oven Sale Amount', default=0.0)
    oven_qty = fields.Integer(string='Oven Qty', default=0)
    knit_sale_amount = fields.Monetary(string='Knit Sale Amount', default=0.0)
    knit_qty = fields.Integer(string='Knit Qty', default=0)

    customer_in = fields.Integer(string='Customer In', default=0)
    purchase = fields.Integer(string='Purchase', default=0)
    not_purchase = fields.Integer(string='Not Purchase', default=0)
    pending_bill_name = fields.Char(string='Pending Bill Name')
    pending_bill_amount = fields.Monetary(string='Pending Bill Amount', default=0.0)

    # ---- Daily Target ----
    daily_target = fields.Monetary(string="Today's Target [TK]", default=0.0)
    achieved_amount = fields.Monetary(string='Achieved In Tk', default=0.0)
    achieved_percent = fields.Float(string='%', compute='_compute_totals', store=True)
    not_achieved_percent = fields.Float(string='Not Achieved %', compute='_compute_totals', store=True)

    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.parent_id or self.env.company)

    @api.depends('cash_sale_city', 'card_ucb', 'm_pay', 'opening_balance',
                 'cash_received', 'total_expense', 'total_vat',
                 'stock_opening_qty', 'received_qty', 'return_qty', 'stock_sale_qty',
                 'daily_target', 'achieved_amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_card_sale = rec.card_ucb
            rec.total_sale = rec.cash_sale_city + rec.card_ucb + rec.m_pay
            rec.closing_balance = (rec.opening_balance + rec.cash_received) - rec.total_expense - rec.total_vat
            rec.closing_store_qty = rec.stock_opening_qty + rec.received_qty - rec.return_qty - rec.stock_sale_qty
            if rec.daily_target:
                rec.achieved_percent = (rec.achieved_amount / rec.daily_target) * 100.0
            else:
                rec.achieved_percent = 0.0
            rec.not_achieved_percent = max(0.0, 100.0 - rec.achieved_percent)
