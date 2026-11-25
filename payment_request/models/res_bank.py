# -*- coding: utf-8 -*-
from odoo import fields, models

# Used when a bank has no "Short Name" typed in yet (matched on the bank name).
_PR_DEFAULT_SHORT_NAMES = (
    ('commercial bank of ceylon', 'CBC'),
    ('mutual trust bank', 'MTB'),
    ('dutch-bangla bank', 'DBBL'),
    ('dutch bangla bank', 'DBBL'),
    ('premier bank', 'PBL'),
)


class ResBank(models.Model):
    _inherit = 'res.bank'

    pr_short_name = fields.Char(
        string='Short Name',
        help='Shown instead of the full bank name on the printed Payment Requisition (e.g. CBC, MTB, DBBL, PBL). '
             'Everywhere else the full bank name is used.')

    def pr_short_label(self):
        """Bank label for the printed Payment Requisition: Short Name -> built-in default -> BIC -> full name."""
        if not self:
            return ''
        self.ensure_one()
        if self.pr_short_name:
            return self.pr_short_name
        name = (self.name or '').lower().replace('.', '').strip()
        for key, short in _PR_DEFAULT_SHORT_NAMES:
            if key in name:
                return short
        return self.bic or self.name or ''
