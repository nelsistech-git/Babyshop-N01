# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'express.approval.mixin']

    def unlink(self):
        if self.env.context.get('express_approval_bypass'):
            return super().unlink()
        for payment in self:
            if payment.state == 'posted':
                action_type = 'supplier_payment' if payment.partner_type == 'supplier' else 'payment'
                payment._express_create_approval(
                    action_type=action_type,
                    old_values=payment._express_snapshot(['amount', 'partner_id', 'journal_id', 'date']),
                    new_values={},
                    reason=self.env.context.get('express_approval_reason'),
                )
                raise UserError(_(
                    'Posted payment %s cannot be deleted directly. A deletion approval request '
                    'has been submitted.') % (payment.name or payment.id))
        return super().unlink()

    def write(self, vals):
        if self.env.context.get('express_approval_bypass'):
            return super().write(vals)
        guarded = {'amount', 'journal_id', 'partner_id', 'date'}
        if guarded.intersection(vals.keys()):
            for payment in self:
                if payment.state == 'posted':
                    action_type = 'supplier_payment' if payment.partner_type == 'supplier' else (
                        'customer_due' if payment.partner_type == 'customer' else 'payment')
                    payment._express_create_approval(
                        action_type=action_type,
                        old_values=payment._express_snapshot(list(guarded)),
                        new_values=vals,
                        reason=self.env.context.get('express_approval_reason'),
                    )
                    raise UserError(_(
                        'Editing posted payment %s requires Manager -> GM -> MD approval. A '
                        'request has been submitted.') % (payment.name or payment.id))
        return super().write(vals)
