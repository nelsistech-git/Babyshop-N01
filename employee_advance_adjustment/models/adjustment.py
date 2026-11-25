from markupsafe import escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.employee_advance.models.amount_words import _amount_to_words_bdt
from odoo.addons.employee_advance.models.base import G_ACCOUNTANT, G_SUPERVISOR


class EmployeeAdvanceAdjustment(models.Model):
    _name = 'employee.advance.adjustment'
    _description = 'Employee Advance Adjustment'
    _inherit = ['employee.advance.base', 'mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    advance_id = fields.Many2one(
        'employee.advance', string='Advance', required=True, tracking=True, ondelete='restrict',
        domain="[('state', '=', 'paid')]")
    employee_id = fields.Many2one(related='advance_id.employee_id', store=True)
    job_title = fields.Char(related='employee_id.job_title', string='Designation')
    department_id = fields.Many2one(
        related='employee_id.department_id', store=True, string='Department')
    work_contact_id = fields.Many2one(related='employee_id.work_contact_id', string='Work Contact')
    company_id = fields.Many2one(related='advance_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date = fields.Date(default=fields.Date.context_today, required=True)
    journal_id = fields.Many2one(
        'account.journal', string='Journal', required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        default=lambda self: self._default_journal())
    advance_account_id = fields.Many2one(related='advance_id.advance_account_id', string='Advance Head')
    advance_amount = fields.Monetary(related='advance_id.amount', string='Advance Amount')
    cash_account_id = fields.Many2one(
        'account.account', string='Cash/Bank (refund or excess payment)',
        compute='_compute_cash_account', store=True, readonly=False,
        domain="[('company_id', '=', company_id), ('deprecated', '=', False)]")
    line_ids = fields.One2many('employee.advance.adjustment.line', 'adjustment_id',
                               string='Expenses', copy=False)
    expense_total = fields.Monetary(compute='_compute_totals', store=True)
    refund_amount = fields.Monetary(
        compute='_compute_totals', store=True, string='Cash Refund by Employee')
    payable_amount = fields.Monetary(
        compute='_compute_totals', store=True, string='Accounts Payable to Employee')
    expense_total_in_words = fields.Char(
        string='Amount in Word', compute='_compute_expense_total_in_words')
    remark = fields.Text(help='Reason when an adjustment is returned.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Supervisor Check'),
        ('checked', 'Accounts Check'),
        ('payable', 'Payable Pending'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True, copy=False)
    adjust_move_id = fields.Many2one('account.move', string='Adjustment Entry', readonly=True, copy=False)
    excess_move_id = fields.Many2one('account.move', string='Excess Payment Entry', readonly=True, copy=False)

    @api.depends('advance_id')
    def _compute_cash_account(self):
        for rec in self:
            if not rec.cash_account_id:
                rec.cash_account_id = rec.advance_id.cash_account_id

    @api.depends('advance_amount', 'line_ids.amount')
    def _compute_totals(self):
        for rec in self:
            total = sum(rec.line_ids.mapped('amount'))
            diff = total - rec.advance_amount
            rec.expense_total = total
            rec.refund_amount = -diff if diff < 0 else 0.0
            rec.payable_amount = diff if diff > 0 else 0.0

    @api.depends('expense_total')
    def _compute_expense_total_in_words(self):
        for rec in self:
            rec.expense_total_in_words = _amount_to_words_bdt(rec.expense_total)

    @api.constrains('advance_id', 'state')
    def _check_one_adjustment(self):
        for rec in self:
            if rec.state == 'cancel':
                continue
            other = self.search_count([
                ('advance_id', '=', rec.advance_id.id),
                ('state', '!=', 'cancel'), ('id', '!=', rec.id)])
            if other:
                raise ValidationError(_('Advance %s already has an adjustment.', rec.advance_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('employee.advance.adjustment') or 'New'
        return super().create(vals_list)

    def unlink(self):
        if any(rec.state not in ('draft', 'cancel') for rec in self):
            raise UserError(_('Only draft or cancelled adjustments can be deleted.'))
        return super().unlink()

    # Level 1: Employee enters expenses and submits
    def action_submit(self):
        self._check_state('draft')
        for rec in self:
            if not rec.line_ids:
                raise UserError(_('Add at least one expense line.'))
            if any(l.amount <= 0 for l in rec.line_ids):
                raise UserError(_('Expense amounts must be greater than zero.'))
        self.write({'state': 'submitted', 'remark': False})

    # Level 2: Supervisor
    def action_check(self):
        self._check_group(G_SUPERVISOR)
        self._check_state('submitted')
        self.write({'state': 'checked', 'remark': False})

    # Return (Supervisor or Accounts), remark required
    def action_return(self):
        for rec in self:
            if rec.state not in ('submitted', 'checked'):
                raise UserError(_('%s cannot be returned in this state.', rec.name))
            if not (rec.remark or '').strip():
                raise UserError(_('Write a remark before returning.'))
            rec._check_group(G_SUPERVISOR if rec.state == 'submitted' else G_ACCOUNTANT)
            rec.message_post(body=escape(_('Returned: %s', rec.remark)))
            rec.state = 'draft'

    # Level 3: Accounts final check and post
    def action_post_entry(self):
        """expense == advance : Dr Expense / Cr Advance
        expense <  advance : Dr Expense, Dr Cash (refund) / Cr Advance
        expense >  advance : Dr Expense / Cr Advance, Cr Accounts Payable
        """
        self._check_group(G_ACCOUNTANT)
        self._check_state('checked')
        for rec in self:
            partner = rec._get_partner()
            adv = rec.advance_account_id
            cur = rec.currency_id
            rec._ensure_reconcile(adv)
            name = _('Advance adjustment %s', rec.name)

            lines = [rec._line(l.name or name, l.account_id, partner, debit=l.amount)
                     for l in rec.line_ids]
            lines.append(rec._line(name, adv, partner, credit=rec.advance_amount))

            has_payable = False
            if not cur.is_zero(rec.refund_amount):
                if not rec.cash_account_id:
                    raise UserError(_('Select the Cash/Bank account in the Accounting tab for the refund.'))
                lines.append(rec._line(_('Cash refund %s', rec.name), rec.cash_account_id, partner,
                                       debit=rec.refund_amount))
            elif not cur.is_zero(rec.payable_amount):
                payable = partner.with_company(rec.company_id).property_account_payable_id
                lines.append(rec._line(_('Payable to employee %s', rec.name), payable, partner,
                                       credit=rec.payable_amount))
                has_payable = True

            move = rec._create_move(lines)
            rec._reconcile(rec.advance_id.payment_move_id | move, adv)
            rec.write({
                'adjust_move_id': move.id,
                'state': 'payable' if has_payable else 'done',
                'remark': False,
            })
            rec.advance_id.sudo().write({'state': 'closed'})

    def action_pay_excess(self):
        """Dr Accounts Payable / Cr Cash, then reconcile the payable."""
        self._check_group(G_ACCOUNTANT)
        self._check_state('payable')
        for rec in self:
            if not rec.cash_account_id:
                raise UserError(_('Select the Cash/Bank account in the Accounting tab.'))
            partner = rec._get_partner()
            payable = partner.with_company(rec.company_id).property_account_payable_id
            name = _('Excess payment %s', rec.name)
            move = rec._create_move([
                rec._line(name, payable, partner, debit=rec.payable_amount),
                rec._line(name, rec.cash_account_id, partner, credit=rec.payable_amount),
            ])
            rec._reconcile(rec.adjust_move_id | move, payable)
            rec.write({'excess_move_id': move.id, 'state': 'done'})

    def action_cancel(self):
        self._check_state('draft', 'submitted')
        self.write({'state': 'cancel'})

    def action_draft(self):
        self._check_state('cancel')
        self.write({'state': 'draft'})


class EmployeeAdvanceAdjustmentLine(models.Model):
    _name = 'employee.advance.adjustment.line'
    _description = 'Employee Advance Adjustment Expense Line'
    _order = 'date, id'

    adjustment_id = fields.Many2one('employee.advance.adjustment', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='adjustment_id.company_id', store=True)
    currency_id = fields.Many2one(related='adjustment_id.currency_id')
    date = fields.Date(default=fields.Date.context_today, required=True)
    name = fields.Char(string='Description', required=True)
    account_id = fields.Many2one('account.account', string='Expense Head', required=True)
    amount = fields.Monetary(required=True)
