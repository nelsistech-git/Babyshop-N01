# -*- coding: utf-8 -*-
from odoo import fields, models


class PaymentRequestBranch(models.Model):
    """Bank branch picked in the "Debit Account Branch" dropdown of a Payment
    Request line. Can be created on the fly from the dropdown."""
    _name = 'payment.request.branch'
    _description = 'Payment Request Bank Branch'
    _order = 'name'

    name = fields.Char(string='Branch Name', required=True)
    bank_id = fields.Many2one('res.bank', string='Bank',
                              help='Optional - when set, this branch is only offered for that bank\'s accounts.')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_bank_uniq', 'unique(name, bank_id)', 'This branch already exists for the selected bank.'),
    ]
