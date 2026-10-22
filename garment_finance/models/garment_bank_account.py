# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentBankAccount(models.Model):
    """Bank Management System (SRS section 16) — garment.bank.account."""
    _name = 'garment.bank.account'
    _description = 'Garment Bank Account'
    _order = 'bank_name'

    bank_name = fields.Char(string='Bank Name', required=True)
    branch = fields.Char(string='Branch')
    account_number = fields.Char(string='Account Number', required=True)
    account_type = fields.Selection([
        ('current', 'Current Account'), ('savings', 'Savings Account'), ('lc_account', 'LC Account'),
    ], string='Account Type', default='current')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    swift_code = fields.Char(string='SWIFT Code')
    current_balance = fields.Monetary(string='Current Balance', currency_field='currency_id')
    transaction_ids = fields.One2many('garment.bank.transaction', 'bank_account_id', string='Transactions')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('account_number_uniq', 'unique(account_number)', 'Account Number must be unique!'),
    ]
