# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentPayment(models.Model):
    """Vendor Payment Management (SRS section 14) — garment.payment.
    Tracks status/aging; the real journal entry lives on the linked
    account.payment when the standard Accounting app is used.

    Also implements the Supplier Payment Workflow / Financial Approval
    Workflow (SRS section 13 & 50, Module 20; section 48, Module 37):
    Supplier Invoice -> Department Verification -> Finance Review ->
    Management Approval -> Bank Payment -> Reconciliation. The approval
    step is gated by garment.payment.approval.rule's amount-banded matrix."""
    _name = 'garment.payment'
    _description = 'Garment Vendor Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # <-- এই লাইনটি যোগ করুন    _order = 'due_date'

    supplier_id = fields.Many2one('garment.supplier', string='Supplier', required=True)
    invoice_reference = fields.Char(string='Supplier Invoice Reference', required=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    invoice_date = fields.Date(string='Invoice Date')
    due_date = fields.Date(string='Due Date')
    paid_amount = fields.Monetary(string='Paid Amount', currency_field='currency_id')
    outstanding_amount = fields.Monetary(string='Outstanding Amount', compute='_compute_outstanding', store=True,
                                          currency_field='currency_id')
    account_payment_id = fields.Many2one('account.payment', string='Linked Accounting Payment')
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'), ('partially_paid', 'Partially Paid'), ('paid', 'Paid'), ('overdue', 'Overdue'),
    ], string='Payment Status', compute='_compute_outstanding', store=True, tracking=True)

    # Financial Approval Workflow / Payment Approval Matrix (SRS section 13,
    # 50 Module 20; section 48 Module 37). Distinct from payment_status above
    # (which tracks how much of the invoice has actually been paid) — this
    # tracks the internal authorization gate that must clear before a bank
    # payment is released.
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending_verification', 'Pending Verification'),
        ('pending_approval', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True)
    verified_by_id = fields.Many2one('res.users', string='Verified By', readonly=True, copy=False)
    verified_date = fields.Datetime(string='Verified On', readonly=True, copy=False)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approval_date = fields.Datetime(string='Approved On', readonly=True, copy=False)
    required_approver_group_id = fields.Many2one('res.groups', string='Required Approver Group',
                                                   compute='_compute_required_approver_group')

    @api.depends('amount')
    def _compute_required_approver_group(self):
        Rule = self.env['garment.payment.approval.rule']
        for rec in self:
            rec.required_approver_group_id = Rule.get_required_group(rec.amount, 'payment')

    def action_submit_for_verification(self):
        self.write({'approval_status': 'pending_verification'})

    def action_verify(self):
        self.write({
            'approval_status': 'pending_approval',
            'verified_by_id': self.env.user.id,
            'verified_date': fields.Datetime.now(),
        })

    def action_approve(self):
        for rec in self:
            group = rec.required_approver_group_id
            if group and group not in self.env.user.groups_id:
                raise UserError(_(
                    'You are not authorized to approve a payment of this amount. '
                    'Required approver group: %s.') % group.name)
            rec.write({
                'approval_status': 'approved',
                'approved_by_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })

    def action_reject(self):
        self.write({'approval_status': 'rejected'})

    def action_reset_to_draft(self):
        self.write({'approval_status': 'draft', 'verified_by_id': False, 'verified_date': False,
                     'approved_by_id': False, 'approval_date': False})

    @api.depends('amount', 'paid_amount', 'due_date')
    def _compute_outstanding(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.outstanding_amount = max(0.0, (rec.amount or 0.0) - (rec.paid_amount or 0.0))
            if rec.outstanding_amount <= 0:
                rec.payment_status = 'paid'
            elif rec.due_date and rec.due_date < today:
                rec.payment_status = 'overdue'
            elif rec.paid_amount:
                rec.payment_status = 'partially_paid'
            else:
                rec.payment_status = 'unpaid'
