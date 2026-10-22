# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentBankTransaction(models.Model):
    """Bank Reconciliation (SRS section 19, Module 20 / section 17, Module
    37) — garment.bank.transaction. Full pipeline: Bank Statement -> Import
    -> Match Transactions -> Reconcile -> Close, backed by
    garment.bank.statement.line for the imported-statement side of the
    match."""
    _name = 'garment.bank.transaction'
    _description = 'Garment Bank Transaction'
    _order = 'transaction_date desc'

    bank_account_id = fields.Many2one('garment.bank.account', string='Bank Account', required=True, ondelete='cascade')
    transaction_date = fields.Date(string='Transaction Date', default=fields.Date.context_today, required=True)
    transaction_type = fields.Selection([
        ('deposit', 'Deposit'), ('withdrawal', 'Withdrawal'), ('lc_payment', 'LC Payment'),
        ('vendor_payment', 'Vendor Payment'), ('receivable_collection', 'Receivable Collection'), ('other', 'Other'),
    ], string='Transaction Type', required=True)
    reference = fields.Char(string='Reference')
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='bank_account_id.currency_id', store=True)
    related_payment_id = fields.Many2one('garment.payment', string='Related Vendor Payment')
    related_receivable_id = fields.Many2one('garment.receivable', string='Related Receivable')
    reconciliation_status = fields.Selection([
        ('unreconciled', 'Unreconciled'), ('matched', 'Matched to Statement'),
        ('reconciled', 'Reconciled'), ('disputed', 'Disputed'), ('closed', 'Closed'),
    ], string='Reconciliation Status', default='unreconciled')

    statement_line_id = fields.Many2one('garment.bank.statement.line', string='Matched Statement Line',
                                         copy=False, readonly=True)
    statement_amount = fields.Monetary(string='Bank Statement Amount', related='statement_line_id.amount',
                                        currency_field='currency_id')
    reconciliation_difference = fields.Monetary(string='Difference', compute='_compute_reconciliation_difference',
                                                  currency_field='currency_id')

    @api.depends('amount', 'statement_line_id.amount')
    def _compute_reconciliation_difference(self):
        for rec in self:
            rec.reconciliation_difference = (
                (rec.amount or 0.0) - rec.statement_line_id.amount) if rec.statement_line_id else 0.0

    def action_reconcile(self):
        for rec in self:
            if rec.reconciliation_status != 'matched':
                raise UserError(_(
                    'Match this transaction to an imported bank statement line before reconciling it '
                    '(Bank Statement -> Import -> Match -> Reconcile -> Close).'))
            rec.reconciliation_status = 'reconciled'
            if rec.statement_line_id:
                rec.statement_line_id.match_status = 'reconciled'

    def action_close(self):
        self.filtered(lambda r: r.reconciliation_status == 'reconciled').write({'reconciliation_status': 'closed'})

    def action_mark_disputed(self):
        self.write({'reconciliation_status': 'disputed'})

    def action_reset_to_unreconciled(self):
        for rec in self:
            if rec.statement_line_id:
                rec.statement_line_id.write({'match_status': 'unmatched', 'matched_transaction_id': False})
            rec.write({'reconciliation_status': 'unreconciled', 'statement_line_id': False})
