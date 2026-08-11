# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    express_pos_default_receipt_format = fields.Selection([
        ('bd', 'Bangladesh (BDT, non-VAT retail receipt)'),
        ('dubai', 'Dubai / UAE (AED, VAT Tax Invoice)'),
    ], string='Default Receipt Format', default='bd',
        help='Fallback billing/receipt layout used for Express POS orders whose branch does not '
             'define its own Receipt Format.')
