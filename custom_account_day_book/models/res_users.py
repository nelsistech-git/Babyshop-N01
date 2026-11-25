# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    bill_approval_step1 = fields.Boolean(
        string='Step 1 - Approve bills up to limit',
        help='Authorized to post/approve vendor bills up to BDT 250,000 '
             '(limit: system parameter custom_account_day_book.approval_limit).')
    bill_approval_step2 = fields.Boolean(
        string='Step 2 - Approve bills above limit (CEO)',
        help='Authorized to post/approve vendor bills exceeding BDT 250,000. '
             'Bills above the limit strictly require this approval (CEO).')
    bill_approval_step3 = fields.Boolean(
        string='Step 3 - Reserved',
        help='Reserved for the third hierarchical approval step.')
