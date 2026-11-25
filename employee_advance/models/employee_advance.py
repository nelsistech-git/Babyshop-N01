from markupsafe import escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment_request_due_sync.models.hr_expense_sheet import get_payment_threshold

from .amount_words import _amount_to_words_bdt
from .base import G_ACCOUNTANT, G_SUPERVISOR


class EmployeeAdvance(models.Model):
    _name = 'employee.advance'
    _description = 'Employee Advance'
    _inherit = ['employee.advance.base', 'mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    employee_id = fields.Many2one(
        'hr.employee', required=True, tracking=True,
        default=lambda self: self.env.user.employee_id)
    job_title = fields.Char(related='employee_id.job_title', string='Designation')
    department_id = fields.Many2one(
        related='employee_id.department_id', store=True, string='Department')
    work_contact_id = fields.Many2one(related='employee_id.work_contact_id', string='Work Contact')
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date = fields.Date(default=fields.Date.context_today, required=True)
    purpose = fields.Char(required=True)
    amount = fields.Monetary(string='Advance Amount', required=True, tracking=True)
    journal_id = fields.Many2one(
        'account.journal', string='Journal', required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        default=lambda self: self._default_journal())
    advance_account_id = fields.Many2one(
        'account.account', string='Advance Head', required=True, tracking=True,
        domain="[('company_id', '=', company_id), ('deprecated', '=', False)]",
        default=lambda self: self._account_by_code('666'),
        help='Chart of Accounts head used to hold the advance (e.g. 666 Advance Against Expenses).')
    cash_account_id = fields.Many2one(
        'account.account', string='Paid From (Cash/Bank)',
        domain="[('company_id', '=', company_id), ('deprecated', '=', False)]",
        default=lambda self: self._account_by_code('701'),
        help='Chart of Accounts head the cash is paid from (e.g. 701 Cash in Hand).')
    remark = fields.Text(help='Reason when a request is returned.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Supervisor Review'),
        ('approved', 'Accounts Review'),
        ('paid', 'Advance Paid'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True, copy=False)
    payment_move_id = fields.Many2one('account.move', string='Advance Entry', readonly=True, copy=False)
    amount_in_words = fields.Char(string='Amount in Word', compute='_compute_amount_in_words')
    requires_payment_request = fields.Boolean(
        string='Payment Request Required', compute='_compute_requires_payment_request',
        help='Above the payment limit (default BDT 5,000) the advance is paid from the bank account '
             'chosen in the Payment Request, not from cash.')
    due_item_ids = fields.One2many('payment.due.item', 'employee_advance_id', string='Due Items')
    payment_request_id = fields.Many2one(
        'payment.request', string='Payment Request', compute='_compute_payment_request_id')

    @api.depends('amount')
    def _compute_amount_in_words(self):
        for rec in self:
            rec.amount_in_words = _amount_to_words_bdt(rec.amount)

    @api.depends('amount')
    def _compute_requires_payment_request(self):
        threshold = get_payment_threshold(self.env)
        for rec in self:
            rec.requires_payment_request = rec.amount > threshold

    @api.depends('due_item_ids.request_id')
    def _compute_payment_request_id(self):
        for rec in self:
            rec.payment_request_id = rec.sudo().due_item_ids.request_id[:1]

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Advance amount must be greater than zero.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('employee.advance') or 'New'
        return super().create(vals_list)

    def unlink(self):
        if any(rec.state not in ('draft', 'cancel') for rec in self):
            raise UserError(_('Only draft or cancelled advances can be deleted.'))
        return super().unlink()

    # Level 1: Employee
    def action_submit(self):
        self._check_state('draft')
        self.write({'state': 'submitted', 'remark': False})

    # Level 2: Supervisor
    def action_approve(self):
        self._check_group(G_SUPERVISOR)
        self._check_state('submitted')
        self.write({'state': 'approved', 'remark': False})

    # Return (Supervisor or Accounts), remark required
    def action_return(self):
        for rec in self:
            if rec.state not in ('submitted', 'approved'):
                raise UserError(_('%s cannot be returned in this state.', rec.name))
            if not (rec.remark or '').strip():
                raise UserError(_('Write a remark before returning.'))
            rec._check_group(G_SUPERVISOR if rec.state == 'submitted' else G_ACCOUNTANT)
            rec._check_not_in_payment_request()
            rec.message_post(body=escape(_('Returned: %s', rec.remark)))
            rec.state = 'draft'

    # Level 3: Accounts (final check and post): Dr Advance head / Cr Cash
    def action_pay(self):
        self._check_group(G_ACCOUNTANT)
        self._check_state('approved')
        for rec in self:
            if rec.requires_payment_request:
                raise UserError(_(
                    '%(name)s is above BDT %(limit)s, so it cannot be paid in cash from here.\n'
                    'Use "Send to Payment Request" (Payment Requests > Due for Payment): it is paid '
                    'from the bank account selected in the Payment Request.',
                    name=rec.name, limit='{:,.0f}'.format(get_payment_threshold(self.env))))
            if not rec.cash_account_id:
                raise UserError(_('Select the Paid From (Cash/Bank) account in the Accounting tab.'))
            rec._ensure_reconcile(rec.advance_account_id)
            partner = rec._get_partner()
            name = _('Advance %s', rec.name)
            move = rec._create_move([
                rec._line(name, rec.advance_account_id, partner, debit=rec.amount),
                rec._line(name, rec.cash_account_id, partner, credit=rec.amount),
            ])
            rec.write({'payment_move_id': move.id, 'state': 'paid', 'remark': False})

    def action_cancel(self):
        self._check_state('draft', 'submitted', 'approved')
        self._check_not_in_payment_request()
        self.write({'state': 'cancel'})

    def action_draft(self):
        self._check_state('cancel')
        self.write({'state': 'draft'})

    # ------------------------------------------------------------------
    # Above the limit: Due for Payment -> Payment Request -> bank
    # ------------------------------------------------------------------
    def _check_not_in_payment_request(self):
        for rec in self:
            items = rec.sudo().due_item_ids.filtered(lambda i: i.state == 'requested')
            if items:
                raise UserError(_(
                    '%(name)s is in Payment Request %(request)s. Cancel or reject that request first.',
                    name=rec.name, request=items[:1].request_id.display_name))

    def action_create_payment_request(self):
        """Accounts Review + above the limit: park the advance in a Draft Payment Request."""
        self.ensure_one()
        self._check_group(G_ACCOUNTANT)
        if not self.requires_payment_request:
            raise UserError(_('Up to BDT %s the advance is paid in cash with "Final Check and Post Entry".')
                            % '{:,.0f}'.format(get_payment_threshold(self.env)))
        self._check_state('approved')
        Item = self.env['payment.due.item'].sudo()
        Item._sync()
        item = Item.search([('employee_advance_id', '=', self.id)], limit=1)
        if not item:
            raise UserError(_('This advance is not listed in "Due for Payment".'))
        if item.state != 'pending':
            raise UserError(_('This advance is already in a Payment Request (or already paid).'))
        action = item.action_create_payment_request()
        self.message_post(body=escape(_('Payment Request created. It is paid from the bank account selected in the Payment Request.')))
        return action

    def _post_from_payment_request(self, request_line):
        """Called when the Payment Request is marked Paid: Dr Advance head / Cr the bank account
        (its journal's account) chosen on the request line. Runs in the request's transaction."""
        self.ensure_one()
        if self.state == 'paid':
            return self.payment_move_id
        self._check_state('approved')
        bank = request_line.own_bank_id
        if not bank:
            raise UserError(_('Select the Debit Account (Our Bank) on the Payment Request line of %s.') % self.name)
        journal = self.env['account.journal'].sudo().search([
            ('type', '=', 'bank'), ('bank_account_id', '=', bank.id),
            ('company_id', '=', self.company_id.id)], limit=1)
        bank_gl = journal.default_account_id
        if not bank_gl:
            raise UserError(_(
                'No Bank journal is linked to account %(acc)s. Open Accounting > Configuration > Journals, '
                'set this account number on the bank journal, then mark the request paid again.',
                acc=bank.display_name))
        self._ensure_reconcile(self.advance_account_id)
        partner = self._get_partner()
        name = _('Advance %s', self.name)
        move = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': request_line.value_date or fields.Date.context_today(self),
            'ref': '%s - %s' % (self.name, request_line.request_id.name),
            'company_id': self.company_id.id,
            'line_ids': [
                self._line(name, self.advance_account_id, partner, debit=self.amount),
                self._line(name, bank_gl, partner, credit=self.amount),
            ],
        })
        move.action_post()
        self.sudo().write({'payment_move_id': move.id, 'state': 'paid', 'remark': False})
        self.message_post(body=escape(_('Paid through Payment Request %s from %s.',
                                        request_line.request_id.display_name, bank.display_name)))
        return move

    # ------------------------------------------------------------------
    # Advance Paid -> Draft
    # ------------------------------------------------------------------
    def action_reset_paid_to_draft(self):
        """Accounts takes a paid advance back to Draft. The advance entry is reversed (the original
        stays for the audit trail). Not possible once the advance is adjusted or when it was paid
        from the bank through a Payment Request."""
        self._check_group(G_ACCOUNTANT)
        for rec in self:
            if rec.state != 'paid':
                raise UserError(_('%s is not in Advance Paid state.', rec.name))
            items = rec.sudo().due_item_ids
            if items:
                raise UserError(_(
                    '%(name)s was paid through Payment Request %(request)s (bank payment), so it cannot '
                    'be reset to Draft.', name=rec.name,
                    request=items[:1].request_id.display_name or ''))
            move = rec.payment_move_id.sudo()
            if move and move.state == 'posted':
                head_lines = move.line_ids.filtered(lambda l: l.account_id == rec.advance_account_id)
                if any(l.reconciled or l.matched_debit_ids or l.matched_credit_ids for l in head_lines):
                    raise UserError(_(
                        '%s is already adjusted against an expense, so it cannot be reset to Draft. '
                        'Undo the adjustment first.', rec.name))
                reversal = move._reverse_moves(
                    [{'ref': _('Reversal of: %s', move.name), 'date': fields.Date.context_today(rec)}],
                    cancel=True)
                rec.message_post(body=escape(_(
                    'Reset to Draft. Advance entry %(old)s reversed by %(new)s.',
                    old=move.name, new=', '.join(reversal.mapped('name')))))
            rec.write({'state': 'draft', 'payment_move_id': False, 'remark': False})

    # ------------------------------------------------------------------
    # Print
    # ------------------------------------------------------------------
    def action_print_advance_claim(self):
        return self.env.ref('employee_advance.action_report_advance_claim').report_action(self)
