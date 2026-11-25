# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

DEFAULT_THRESHOLD = 5000.0


def get_payment_threshold(env):
    """BDT limit: up to and including it -> pay directly from Expenses,
    above it -> Payment Request (Due for Payment)."""
    value = env['ir.config_parameter'].sudo().get_param('payment_request_due_sync.expense_min_amount')
    try:
        return float(value) if value else DEFAULT_THRESHOLD
    except ValueError:
        return DEFAULT_THRESHOLD


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    requires_payment_request = fields.Boolean(
        string='Payment Request Required', compute='_compute_requires_payment_request',
        help='Total is above the payment limit (default BDT 5,000): it must be paid through a '
             'Payment Request, not with "Register Payment".')
    due_item_ids = fields.One2many('payment.due.item', 'sheet_id', string='Due Items')
    payment_request_id = fields.Many2one(
        'payment.request', string='Payment Request', compute='_compute_payment_request_id')

    def _amount_in_company_currency(self):
        self.ensure_one()
        amount = self.total_amount
        company = self.company_id
        if self.currency_id and company and self.currency_id != company.currency_id:
            amount = self.currency_id._convert(
                amount, company.currency_id, company, fields.Date.context_today(self))
        return amount

    @api.depends('total_amount', 'currency_id', 'company_id')
    def _compute_requires_payment_request(self):
        threshold = get_payment_threshold(self.env)
        for sheet in self:
            sheet.requires_payment_request = sheet._amount_in_company_currency() > threshold

    @api.depends('due_item_ids.request_id')
    def _compute_payment_request_id(self):
        for sheet in self:
            sheet.payment_request_id = sheet.sudo().due_item_ids.request_id[:1]

    def action_register_payment(self):
        blocked = self.filtered('requires_payment_request')
        if blocked:
            raise UserError(_(
                'Expense report(s) %(names)s are above BDT %(limit)s, so they cannot be paid from '
                'the Expenses module.\nUse "Send to Payment Request" (Payment Requests > Due for '
                'Payment) instead.',
                names=', '.join(blocked.mapped('name')),
                limit='{:,.0f}'.format(get_payment_threshold(self.env))))
        return super().action_register_payment()

    def action_create_payment_request(self):
        self.ensure_one()
        if not self.requires_payment_request:
            raise UserError(_('Up to BDT %s you can pay directly with "Register Payment".')
                            % '{:,.0f}'.format(get_payment_threshold(self.env)))
        if self.state not in ('approve', 'post'):
            raise UserError(_('Only approved expense reports can be sent to a Payment Request.'))
        Item = self.env['payment.due.item'].sudo()
        Item._sync()
        item = Item.search([('sheet_id', '=', self.id)], limit=1)
        if not item:
            raise UserError(_('This report is not listed in "Due for Payment".'))
        if item.state != 'pending':
            raise UserError(_('This report is already in a Payment Request (or already paid).'))
        return item.action_create_payment_request()


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        # Vendor bills: no direct payment from Accounting, only through a Payment Request
        self.line_ids.move_id._check_not_paid_directly()
        # Same rule when someone opens the report's journal entry and presses Pay there.
        if 'expense_sheet_id' in self.env['account.move']._fields:
            sheets = self.line_ids.move_id.expense_sheet_id
            blocked = sheets.filtered('requires_payment_request')
            if blocked:
                raise UserError(_(
                    'Expense report(s) %s are above BDT %s: pay them through a Payment Request.')
                    % (', '.join(blocked.mapped('name')),
                       '{:,.0f}'.format(get_payment_threshold(self.env))))
        return super().action_create_payments()
