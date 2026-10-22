# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentExpense(models.Model):
    """Expense Management System (SRS section 13) — garment.expense."""
    _name = 'garment.expense'
    _description = 'Garment Expense'
    _inherit = ['mail.thread']
    _order = 'expense_date desc'

    expense_category = fields.Selection([
        ('factory', 'Factory Expense'), ('office', 'Office Expense'), ('travel', 'Travel Expense'),
        ('maintenance', 'Maintenance Expense'), ('utility', 'Utility Expense'), ('other', 'Other'),
    ], string='Expense Category', required=True)
    description = fields.Char(string='Description')
    cost_center_id = fields.Many2one('garment.cost.center', string='Department / Cost Center', required=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    expense_date = fields.Date(string='Expense Date', default=fields.Date.context_today, required=True)
    requested_by_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user)
    attachment = fields.Binary(string='Receipt/Invoice', attachment=True)
    status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    # Payment Approval Matrix reused for expenses (SRS section 50 Module 20 /
    # 48 Module 37 Financial Approval Workflow applies to both AP payments
    # and factory expenses) — see garment.payment.approval.rule.
    required_approver_group_id = fields.Many2one('res.groups', string='Required Approver Group',
                                                   compute='_compute_required_approver_group')

    @api.depends('amount')
    def _compute_required_approver_group(self):
        Rule = self.env['garment.payment.approval.rule']
        for rec in self:
            rec.required_approver_group_id = Rule.get_required_group(rec.amount, 'expense')

    def action_approve(self):
        for rec in self:
            group = rec.required_approver_group_id
            if group and group not in self.env.user.groups_id:
                raise UserError(_(
                    'You are not authorized to approve an expense of this amount. '
                    'Required approver group: %s.') % group.name)
        self.write({'status': 'approved'})

    def action_reject(self):
        self.write({'status': 'rejected'})
