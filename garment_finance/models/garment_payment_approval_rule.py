# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Financial Approval Workflow / Payment Approval Matrix (SRS section 50,
Module 20 — "Purchase Payment Approval": Supplier Invoice -> Department
Verification -> Finance Review -> Management Approval -> Bank Payment; and
SRS section 48, Module 37 — "Financial Approval Workflow" approval levels).

Amount-banded routing table: which res.groups must approve a Vendor
Payment / Expense of a given amount. garment.payment and garment.expense
both call get_required_group() rather than hard-coding a threshold, so
Finance can retune the matrix (e.g. raise the CFO threshold) without a
code change.
"""
from odoo import api, fields, models


class GarmentPaymentApprovalRule(models.Model):
    _name = 'garment.payment.approval.rule'
    _description = 'Garment Finance Payment Approval Matrix'
    _order = 'sequence, min_amount'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(default=10)
    applies_to = fields.Selection([
        ('payment', 'Vendor Payment'), ('expense', 'Expense'), ('both', 'Both'),
    ], string='Applies To', default='both', required=True)
    min_amount = fields.Monetary(string='From Amount', required=True, currency_field='currency_id')
    max_amount = fields.Monetary(string='To Amount (0 = no upper limit)', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    approver_group_id = fields.Many2one('res.groups', string='Required Approver Group', required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _matches(self, amount, doc_type):
        self.ensure_one()
        if self.applies_to not in ('both', doc_type):
            return False
        if amount < self.min_amount:
            return False
        if self.max_amount and amount > self.max_amount:
            return False
        return True

    @api.model
    def get_required_group(self, amount, doc_type):
        """Returns the res.groups record required to approve a payment/expense
        of `amount` (a garment.payment or garment.expense amount). Falls back
        to the module's Finance Manager group if no matrix rule matches, so
        approval is never silently ungated."""
        rules = self.search([('applies_to', 'in', (doc_type, 'both'))])
        for rule in rules:
            if rule._matches(amount, doc_type):
                return rule.approver_group_id
        return self.env.ref('garment_finance.group_finance_manager', raise_if_not_found=False)
