# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        """Vendor bills can only be paid once they are 'Due for Payment' (posted by an authorized user)."""
        for wizard in self:
            blocked = wizard.line_ids.move_id.filtered(
                lambda m: m.move_type in ('in_invoice', 'in_receipt') and m.bill_stage != 'due_for_payment')
            if blocked:
                raise UserError(_(
                    "These vendor bills must be posted (approved) before payment:\n%s",
                    '\n'.join(blocked.mapped(lambda m: m.name or m.ref or str(m.id)))))
        return super().action_create_payments()
