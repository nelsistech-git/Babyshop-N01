# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Bank Reconciliation (SRS section 19, Module 20 / section 17, Module 37):
    Bank Statement -> Import -> Match Transactions -> Reconcile -> Close

garment.bank.statement.line represents one line of an imported (or
manually entered) bank statement, kept separate from garment.bank.
transaction (the ERP-side ledger entry) so the two can be matched against
each other rather than assumed identical — the actual "reconciliation"
step the previous version of this module was missing (it only let a user
flip a transaction straight to Reconciled with no statement to check it
against).
"""
from odoo import fields, models


class GarmentBankStatementLine(models.Model):
    _name = 'garment.bank.statement.line'
    _description = 'Garment Bank Statement Line (Import)'
    _order = 'statement_date desc'

    bank_account_id = fields.Many2one('garment.bank.account', string='Bank Account', required=True,
                                       ondelete='cascade')
    statement_date = fields.Date(string='Statement Date', required=True, default=fields.Date.context_today)
    description = fields.Char(string='Description')
    reference = fields.Char(string='Bank Reference')
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='bank_account_id.currency_id', store=True)

    match_status = fields.Selection([
        ('unmatched', 'Unmatched'), ('matched', 'Matched'), ('reconciled', 'Reconciled'),
    ], string='Match Status', default='unmatched', tracking=False)
    matched_transaction_id = fields.Many2one('garment.bank.transaction', string='Matched ERP Transaction',
                                              copy=False, readonly=True)

    imported_by_id = fields.Many2one('res.users', string='Imported By', default=lambda s: s.env.user)
    import_date = fields.Datetime(string='Imported On', default=fields.Datetime.now)

    def action_auto_match(self):
        """Matches each unmatched statement line to an unreconciled ERP
        garment.bank.transaction on the same bank account with the same
        amount and a transaction date within 5 days of the statement date.
        Only matches when exactly one candidate is found — an ambiguous
        match is left for manual reconciliation rather than guessed."""
        Transaction = self.env['garment.bank.transaction']
        for rec in self:
            if rec.match_status != 'unmatched':
                continue
            candidates = Transaction.search([
                ('bank_account_id', '=', rec.bank_account_id.id),
                ('reconciliation_status', '=', 'unreconciled'),
                ('amount', '=', rec.amount),
            ])
            if rec.statement_date:
                candidates = candidates.filtered(
                    lambda t: t.transaction_date and abs((t.transaction_date - rec.statement_date).days) <= 5)
            if len(candidates) == 1:
                txn = candidates
                txn.write({'reconciliation_status': 'matched', 'statement_line_id': rec.id})
                rec.write({'match_status': 'matched', 'matched_transaction_id': txn.id})
        return True

    def action_reset_match(self):
        for rec in self:
            if rec.matched_transaction_id:
                rec.matched_transaction_id.write({'reconciliation_status': 'unreconciled', 'statement_line_id': False})
            rec.write({'match_status': 'unmatched', 'matched_transaction_id': False})
