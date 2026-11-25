# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveSupportDoc(models.Model):
    _name = 'account.move.support.doc'
    _description = 'Vendor Bill Supporting Document'
    _order = 'sequence, id'

    move_id = fields.Many2one('account.move', string='Bill', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    doc_type = fields.Selection([
        ('invoice', 'Invoice'),
        ('po', 'Purchase Order (PO)'),
        ('grn', 'Goods Receipt Note (GRN)'),
        ('work_order', 'Work Order'),
        ('other', 'Other'),
    ], string='Document Type', required=True, default='invoice')
    reference = fields.Char(string='Reference No.')
    file = fields.Binary(string='File', attachment=True)
    filename = fields.Char(string='File Name')
    note = fields.Char(string='Note')
