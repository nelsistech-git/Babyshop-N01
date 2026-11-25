# -*- coding: utf-8 -*-
from odoo import fields, models


class PaymentRequestLine(models.Model):
    _inherit = 'payment.request.line'

    due_item_id = fields.Many2one(
        'payment.due.item', string='Due Item', copy=False, index=True, ondelete='set null',
        help='The "Due for Payment" row this line was created from.')
    expense_sheet_id = fields.Many2one(
        'hr.expense.sheet', string='Expense Report', copy=False, readonly=True, index=True,
        help='Set when this line settles an approved Expense report.')


class PaymentRequest(models.Model):
    _inherit = 'payment.request'

    def action_mark_paid(self):
        res = super().action_mark_paid()
        # rows of a paid request leave "Due for Payment"; let each source record know
        self.sudo().line_ids.due_item_id._settle_source()
        return res
