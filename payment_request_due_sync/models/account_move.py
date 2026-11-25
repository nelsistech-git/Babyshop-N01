# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post_for_payment(self):
        """Head of Finance posts the bill -> it lands in Payment Requests > Due for Payment at once."""
        res = super().action_post_for_payment()
        self.env['payment.due.item'].sudo()._sync()
        return res

    def _check_not_paid_directly(self):
        """Vendor bills are paid ONLY through a Payment Request (which posts the accounting payment
        itself) - a second 'Register Payment' in Accounting would pay the same bill twice."""
        bills = self.filtered(lambda m: m.move_type in ('in_invoice', 'in_receipt'))
        if bills:
            raise UserError(_(
                "Vendor bills cannot be paid with 'Register Payment' in Accounting.\n"
                "Pay them from Payment Requests (Due for Payment > Create Payment Request > Mark Paid) - "
                "the bill is marked paid in Accounting automatically.\n\nBills: %s",
                ', '.join(bills.mapped(lambda m: m.name or m.ref or str(m.id)))))
