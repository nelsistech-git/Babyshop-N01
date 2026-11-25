# -*- coding: utf-8 -*-
from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError

# Hard-coded accounting rule for Expense Reports paid by the employee (own account):
#   Dr  Expense Account of each line's product (Expense Category)
#   Cr  701 Cash in Hand                       when the report total is 5,000 or less
#   Cr  800 Account Payable (vendor bill)      when the report total is above 5,000 -> Request for Payment
EXPENSE_CASH_ACCOUNT_CODE = '701'
EXPENSE_PAYABLE_ACCOUNT_CODE = '800'      # Account Payable - always, for reports above the limit
EXPENSE_CASH_LIMIT = 5000.0


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_expense_cash_settled = fields.Boolean(
        string='Expense Paid in Cash', copy=False, readonly=True,
        help='Journal entry of an Expense Report of 5,000 or less: credited to Cash in Hand, so it is '
             'already settled.')

    def _post(self, soft=True):
        """Vendor bills (Accounting) with an Expense Category product are ALWAYS debited to the Expense
        Account set on that product - whatever account was typed or defaulted on the line."""
        for move in self.filtered(lambda m: m.move_type in ('in_invoice', 'in_refund') and m.state == 'draft'):
            for line in move.invoice_line_ids.filtered(
                    lambda l: l.display_type == 'product' and l.product_id and l.product_id.can_be_expensed):
                account = line.product_id.product_tmpl_id.with_company(move.company_id).property_account_expense_id
                if account and line.account_id != account:
                    line.account_id = account
        return super()._post(soft)


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    sheet_number = fields.Char(
        string='Expense Ref. No.', readonly=True, copy=False, index=True, default='New',
        help='Automatic document number of the expense report (sequence).')
    submission_date = fields.Date(
        string='Submission Date', readonly=True, copy=False,
        help='The date the employee submitted this report.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sheet_number') or vals.get('sheet_number') == 'New':
                vals['sheet_number'] = self.env['ir.sequence'].next_by_code('hr.expense.sheet.number') or 'New'
            if vals.get('state') == 'submit' and not vals.get('submission_date'):
                vals['submission_date'] = fields.Date.context_today(self)
        return super().create(vals_list)

    def write(self, vals):
        # every (re)submission stamps today's date; submit_sheet only writes state='submit'
        if vals.get('state') == 'submit' and 'submission_date' not in vals:
            vals = dict(vals, submission_date=fields.Date.context_today(self))
        return super().write(vals)

    def action_create_payment_request(self):
        """A report whose conveyance sheet already has its own Due-for-Payment row is not listed
        under its own name: pick up that row instead of failing with 'not listed'."""
        self.ensure_one()
        Item = self.env['payment.due.item'].sudo()
        Item._sync()
        if not Item.search([('sheet_id', '=', self.id)], limit=1):
            csheets = self.expense_line_ids.sudo().conveyance_sheet_ids
            pending = Item.search([('source_type', '=', 'conveyance'),
                                   ('conveyance_sheet_id', 'in', csheets.ids),
                                   ('state', '=', 'pending')])
            if pending:
                return pending.action_create_payment_request()
        return super().action_create_payment_request()

    # ------------------------------------------------------------------ Cash / Payable rule
    def _expense_cash_eligible(self):
        self.ensure_one()
        return (self.payment_mode == 'own_account'
                and 0 < self.total_amount <= EXPENSE_CASH_LIMIT
                and not self.expense_line_ids.mapped('tax_ids')
                and not self.is_multiple_currency)

    def _prepare_bills_vals(self):
        """Above 5,000 the standard vendor bill is used, but every line is debited to the Expense
        Account of its own Expense Category (detail lines are split by Category)."""
        vals = super()._prepare_bills_vals()
        partner = self.employee_id.sudo().work_contact_id
        lines = []
        for exp in self.expense_line_ids:
            splits = exp._expense_debit_splits()
            if len(splits) == 1:
                std = exp._prepare_move_lines_vals()          # keeps quantity / taxes of a plain expense
                std['account_id'] = splits[0]['account'].id
                lines.append(Command.create(std))
            else:
                for sp in splits:
                    lines.append(Command.create({
                        'name': sp['name'], 'account_id': sp['account'].id, 'product_id': sp['product'].id,
                        'quantity': 1.0, 'price_unit': sp['amount'], 'expense_id': exp.id,
                        'partner_id': partner.id, 'tax_ids': [Command.clear()],
                    }))
        vals['line_ids'] = lines
        return vals

    def _force_payable_account(self, moves):
        """The Credit of every bill above 5,000 is ALWAYS account 800 Account Payable."""
        Account = self.env['account.account'].sudo()
        for move in moves.filtered(lambda m: m.move_type == 'in_invoice' and m.expense_sheet_id):
            ap = Account.search([('code', '=', EXPENSE_PAYABLE_ACCOUNT_CODE),
                                 ('company_id', '=', move.company_id.id)], limit=1)
            if not ap:
                raise UserError(_('Account %s (Account Payable) was not found.') % EXPENSE_PAYABLE_ACCOUNT_CODE)
            pay = move.line_ids.filtered(lambda l: l.display_type == 'payment_term' and l.account_id != ap)
            if pay:
                move.button_draft()
                pay.write({'account_id': ap.id})
                move.action_post()

    def _do_create_moves(self):
        cash_sheets = self.filtered(lambda s: s._expense_cash_eligible())
        other = self - cash_sheets
        moves = super(HrExpenseSheet, other)._do_create_moves() if other else self.env['account.move']
        if other:
            self._force_payable_account(moves)
            # above 5,000 -> straight into "Due for Payment" (Request for Payment)
            self.env['payment.due.item'].sudo()._sync()
        if cash_sheets:
            moves |= cash_sheets._create_cash_moves()
            cash_sheets.activity_update()
        return moves

    def _create_cash_moves(self):
        """Report total <= 5,000: Dr product Expense Account / Cr 701 Cash in Hand."""
        Account = self.env['account.account'].sudo()
        Journal = self.env['account.journal'].sudo()
        vals_list = []
        for sheet in self:
            company = sheet.company_id
            cash = Account.search([('code', '=', EXPENSE_CASH_ACCOUNT_CODE),
                                   ('company_id', '=', company.id)], limit=1)
            if not cash:
                raise UserError(_('Account %s (Cash in Hand) was not found. Please create it in the '
                                  'chart of accounts.') % EXPENSE_CASH_ACCOUNT_CODE)
            journal = Journal.search([('type', '=', 'general'), ('company_id', '=', company.id)], limit=1)
            if not journal:
                raise UserError(_('No Miscellaneous (general) journal found.'))
            partner = sheet.employee_id.sudo().work_contact_id
            lines, total = [], 0.0
            for exp in sheet.expense_line_ids:
                for sp in exp._expense_debit_splits():
                    lines.append((0, 0, {
                        'name': sp['name'], 'account_id': sp['account'].id, 'partner_id': partner.id,
                        'product_id': sp['product'].id or False,
                        'debit': sp['amount'], 'credit': 0.0, 'expense_id': exp.id,
                    }))
                    total += sp['amount']
            lines.append((0, 0, {
                'name': '%s: %s' % (sheet.employee_id.name, sheet.name), 'account_id': cash.id,
                'partner_id': partner.id, 'debit': 0.0, 'credit': total,
            }))
            vals_list.append({
                'move_type': 'entry',
                'journal_id': journal.id,
                'date': sheet.accounting_date or max(sheet.expense_line_ids.filtered('date').mapped('date'),
                                                     default=fields.Date.context_today(sheet)),
                'ref': sheet.name,
                'expense_sheet_id': sheet.id,
                'x_expense_cash_settled': True,
                'line_ids': lines,
            })
        moves = self.env['account.move'].create(vals_list)
        moves.action_post()
        return moves

    @api.depends('account_move_ids.payment_state', 'account_move_ids.amount_residual',
                 'account_move_ids.x_expense_cash_settled')
    def _compute_from_account_move_ids(self):
        super()._compute_from_account_move_ids()
        for sheet in self:
            moves = sheet.account_move_ids.filtered(lambda m: not m.reversal_move_id)
            if moves and all(moves.mapped('x_expense_cash_settled')):
                sheet.amount_residual = 0.0
                sheet.payment_state = 'paid'
