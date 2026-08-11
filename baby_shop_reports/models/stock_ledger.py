# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BabyShopStockLedger(models.Model):
    """Daily Stock Ledger - entered per showroom/branch, per day.

    Mirrors the manual 'Stock Leadger' sheet: Opening / Received / Issued /
    Balance, grouped by Area.
    """
    _name = 'baby.shop.stock.ledger'
    _description = 'Baby Shop - Daily Stock Ledger Line'
    _order = 'date desc, area_name, showroom_id'
    _rec_name = 'showroom_id'

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, index=True)
    area_name = fields.Char(string='Area', required=True, index=True,
                             help="e.g. 'Area-02' as printed in the report title")

    showroom_id = fields.Many2one(
        'res.company', string='Show Room Name', required=True,
        domain="[('parent_id', '!=', False)]", index=True,
    )

    opening_qty = fields.Float(string='Opening', default=0.0)

    # ---- Received ----
    invoice_no = fields.Char(string='Invoice No')
    invoice_rcv_qty = fields.Float(string='Invoice/Rcv Qty', default=0.0)
    rcv_from = fields.Char(string='RCV From')
    total_received_qty = fields.Float(string='Total Qty (Received)', compute='_compute_totals', store=True)

    # ---- Issued ----
    sales_qty = fields.Float(string='Sales Qty', default=0.0)
    return_invoice = fields.Char(string='Return Invoice')
    return_to = fields.Char(string='Return To')
    return_qty = fields.Float(string='Return Qty', default=0.0)
    total_issued_qty = fields.Float(string='Total Qty (Issued)', compute='_compute_totals', store=True)

    balance_qty = fields.Float(string='Balance', compute='_compute_totals', store=True)

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.parent_id or self.env.company)

    @api.depends('opening_qty', 'invoice_rcv_qty', 'sales_qty', 'return_qty')
    def _compute_totals(self):
        for rec in self:
            rec.total_received_qty = rec.invoice_rcv_qty
            rec.total_issued_qty = rec.sales_qty + rec.return_qty
            rec.balance_qty = rec.opening_qty + rec.total_received_qty - rec.total_issued_qty
