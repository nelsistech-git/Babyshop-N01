# -*- coding: utf-8 -*-
from odoo import fields, models


class DailyReportSaleLine(models.Model):
    """Section 1: Showroom Sale of Head Office <- account.move (out_invoice)."""
    _name = 'daily.report.sale.line'
    _description = 'Daily Report - Showroom Sale Line'
    _order = 'id'

    report_id = fields.Many2one(
        'daily.sale.official.cost.report', required=True, ondelete='cascade')
    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer Name', readonly=True)
    paid_advance = fields.Monetary(string='Paid/Advance', readonly=True)
    invoice_total = fields.Monetary(string='Condition (Invoice Total)', readonly=True)
    due_amount = fields.Monetary(string='Due', readonly=True)
    currency_id = fields.Many2one(related='report_id.currency_id')


class DailyReportCostLine(models.Model):
    """Section 2: Official Cost <- account.move.line (expense accounts)."""
    _name = 'daily.report.cost.line'
    _description = 'Daily Report - Official Cost Line'
    _order = 'id'

    report_id = fields.Many2one(
        'daily.sale.official.cost.report', required=True, ondelete='cascade')
    move_line_id = fields.Many2one('account.move.line', string='Journal Item', readonly=True)
    cost_detail = fields.Char(string='Cost Detail', readonly=True)
    payee = fields.Char(string='Name', readonly=True)
    amount = fields.Monetary(string='TK', readonly=True)
    currency_id = fields.Many2one(related='report_id.currency_id')


class DailyReportSupplierLine(models.Model):
    """Section 3: Supplier Transaction <- account.payment (outbound)."""
    _name = 'daily.report.supplier.line'
    _description = 'Daily Report - Supplier Transaction Line'
    _order = 'id'

    report_id = fields.Many2one(
        'daily.sale.official.cost.report', required=True, ondelete='cascade')
    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Name', readonly=True)
    payment_method = fields.Char(string='Type', readonly=True)
    amount = fields.Monetary(string='Amount', readonly=True)
    currency_id = fields.Many2one(related='report_id.currency_id')


class DailyReportCollectionLine(models.Model):
    """Section 4: Mobile & Bank Transaction <- account.payment (inbound)."""
    _name = 'daily.report.collection.line'
    _description = 'Daily Report - Mobile & Bank Collection Line'
    _order = 'id'

    report_id = fields.Many2one(
        'daily.sale.official.cost.report', required=True, ondelete='cascade')
    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer Name', readonly=True)
    channel = fields.Selection([
        ('bank', 'Bank / Draft'),
        ('bkash', 'bKash / Mobile'),
    ], string='Channel', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Bank/Journal', readonly=True)
    payment_ref = fields.Char(string='Note / Reference', readonly=True)
    amount = fields.Monetary(string='Amount', readonly=True)
    currency_id = fields.Many2one(related='report_id.currency_id')
