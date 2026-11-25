# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

BILL_TYPES = ('in_invoice', 'in_receipt')
APPROVAL_LIMIT_PARAM = 'custom_account_day_book.approval_limit'
DEFAULT_APPROVAL_LIMIT = 250000.0


class AccountMove(models.Model):
    _inherit = 'account.move'

    bill_stage = fields.Selection(
        [('pending', 'Pending Approval'), ('due_for_payment', 'Due for Payment')],
        string='Bill Stage', default='pending', copy=False, readonly=True,
        tracking=True, index=True,
        help="'Due for Payment' is reached when an authorized user clicks 'Post' on the validated vendor bill.")
    approved_by_id = fields.Many2one('res.users', string='Posted By', copy=False, readonly=True)
    approved_date = fields.Datetime(string='Posted On', copy=False, readonly=True)
    support_doc_ids = fields.One2many(
        'account.move.support.doc', 'move_id', string='Supporting Documents', copy=False)

    bill_gross_amount = fields.Monetary(
        string='Bill Amount (incl. VAT)', compute='_compute_bill_gross_amount',
        currency_field='company_currency_id',
        help='Total bill value including VAT, in company currency. Used for the approval matrix.')
    bill_required_step = fields.Selection(
        [('1', 'Step 1'), ('2', 'Step 2 (CEO)')], string='Required Approval',
        compute='_compute_bill_required_step')
    bill_approval_note = fields.Char(compute='_compute_bill_required_step')
    can_user_post_bill = fields.Boolean(compute='_compute_can_user_post_bill')

    # ------------------------------------------------------------------ helpers
    @api.model
    def _get_bill_approval_limit(self):
        value = self.env['ir.config_parameter'].sudo().get_param(
            APPROVAL_LIMIT_PARAM, default=str(DEFAULT_APPROVAL_LIMIT))
        try:
            return float(value)
        except (TypeError, ValueError):
            return DEFAULT_APPROVAL_LIMIT

    def _is_vendor_bill(self):
        self.ensure_one()
        return self.move_type in BILL_TYPES

    @staticmethod
    def _user_has_step(user, step):
        # hierarchical: a Step 2 (CEO) / Step 3 approver can also approve Step 1 bills
        if step == '1':
            return bool(user.bill_approval_step1 or user.bill_approval_step2 or user.bill_approval_step3)
        return bool(user.bill_approval_step2 or user.bill_approval_step3)

    # ------------------------------------------------------------------ computes
    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.display_type', 'move_type')
    def _compute_bill_gross_amount(self):
        for move in self:
            lines = move.line_ids.filtered(lambda l: l.display_type in ('product', 'tax'))
            if move.move_type == 'in_refund':
                move.bill_gross_amount = sum(lines.mapped('credit'))
            else:
                move.bill_gross_amount = sum(lines.mapped('debit'))

    @api.depends('bill_gross_amount', 'move_type')
    def _compute_bill_required_step(self):
        limit = self._get_bill_approval_limit()
        for move in self:
            if move.move_type not in BILL_TYPES:
                move.bill_required_step = False
                move.bill_approval_note = False
                continue
            rounding = move.company_currency_id.rounding or 0.01
            if float_compare(move.bill_gross_amount, limit, precision_rounding=rounding) <= 0:
                move.bill_required_step = '1'
                move.bill_approval_note = _(
                    "Approval required: Step 1 authorized user (bills up to BDT %s).", f"{limit:,.0f}")
            else:
                move.bill_required_step = '2'
                move.bill_approval_note = _(
                    "Approval required: Step 2 authorized user - CEO (bills above BDT %s).", f"{limit:,.0f}")

    @api.depends_context('uid')
    @api.depends('bill_required_step', 'bill_stage', 'state', 'payment_state', 'move_type')
    def _compute_can_user_post_bill(self):
        user = self.env.user
        for move in self:
            move.can_user_post_bill = bool(
                move.move_type in BILL_TYPES
                and move.state == 'posted'
                and move.bill_stage == 'pending'
                and move.payment_state in ('not_paid', 'partial')
                and move.bill_required_step
                and self._user_has_step(user, move.bill_required_step)
            )

    # ------------------------------------------------------------------ checks
    def _check_support_documents(self):
        for move in self:
            has_tab_file = any(doc.file for doc in move.support_doc_ids)
            # files attached through the chatter (Log note / Send message / paperclip) count too
            has_chatter_file = bool(self.env['ir.attachment'].sudo().search_count([
                ('res_model', '=', 'account.move'), ('res_id', '=', move.id)]))
            if not (has_tab_file or has_chatter_file):
                raise UserError(_(
                    "Supporting documents are mandatory.\n"
                    "Attach at least one document (Invoice, PO, GRN, Work Order, ...) in the "
                    "'Supporting Documents' tab or through a Log note of bill %s before posting.",
                    move.name or move.ref or ''))

    def _check_user_can_post_bill(self):
        user = self.env.user
        for move in self:
            step = move.bill_required_step
            if not self._user_has_step(user, step):
                limit = self._get_bill_approval_limit()
                if step == '1':
                    raise UserError(_(
                        "You are not authorized to post this bill.\n"
                        "Bills up to BDT %s need the 'Step 1' approval right on your user profile.",
                        f"{limit:,.0f}"))
                raise UserError(_(
                    "You are not authorized to post this bill.\n"
                    "Bills above BDT %s need CEO approval ('Step 2' approval right on your user profile).",
                    f"{limit:,.0f}"))

    # ------------------------------------------------------------------ actions
    def action_post_for_payment(self):
        """Button 'Post' (formerly 'Register Payment') on vendor bills: moves the bill to 'Due for Payment'."""
        for move in self:
            if move.move_type not in BILL_TYPES:
                raise UserError(_("Only vendor bills can be posted for payment."))
            if move.state != 'posted':
                raise UserError(_("Please confirm (validate) the bill first."))
            if move.payment_state not in ('not_paid', 'partial'):
                raise UserError(_("Bill %s is already paid.", move.name))
            if move.bill_stage == 'due_for_payment':
                continue
            move._check_support_documents()
            move._check_user_can_post_bill()
            move.write({
                'bill_stage': 'due_for_payment',
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            move.message_post(body=_(
                "Bill posted by %(user)s and moved to <b>Due for Payment</b> (amount incl. VAT: %(amount)s).",
                user=self.env.user.name, amount=f"{move.bill_gross_amount:,.2f}"))
        return True

    def button_draft(self):
        res = super().button_draft()
        self.filtered(lambda m: m.move_type in BILL_TYPES)._reset_bill_stage()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        self.filtered(lambda m: m.move_type in BILL_TYPES)._reset_bill_stage()
        return res

    def _reset_bill_stage(self):
        self.filtered(lambda m: m.bill_stage != 'pending' or m.approved_by_id).write({
            'bill_stage': 'pending',
            'approved_by_id': False,
            'approved_date': False,
        })
