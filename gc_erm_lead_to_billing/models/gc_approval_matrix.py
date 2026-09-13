# -*- coding: utf-8 -*-
"""Approval matrix and amount based approval thresholds (SRS 59 / 60)."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

APPROVAL_DOCUMENT_SELECTION = [
    ('lead', 'Lead'),
    ('technical_report', 'Technical Report'),
    ('proposal', 'Proposal'),
    ('work_order', 'Work Order'),
    ('procurement', 'Procurement Request'),
    ('invoice', 'Invoice'),
]


class GcErmApprovalMatrix(models.Model):
    _name = 'gc.erm.approval.matrix'
    _description = 'GC ERM Approval Matrix'
    _order = 'document_type, amount_from'

    name = fields.Char(string='Rule Name', compute='_compute_name', store=True)
    document_type = fields.Selection(
        APPROVAL_DOCUMENT_SELECTION, string='Document Type', required=True,
        index=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', readonly=True)
    active = fields.Boolean(default=True)

    amount_from = fields.Monetary(
        string='Amount From', currency_field='currency_id', default=0.0)
    amount_to = fields.Monetary(
        string='Amount To', currency_field='currency_id', default=0.0,
        help='Upper bound of the band. Leave at 0 for "no upper limit".')

    approver_group_id = fields.Many2one(
        'res.groups', string='Approver Group', required=True,
        help='Security group allowed to approve documents in this band.')
    approver_user_ids = fields.Many2many(
        'res.users', string='Named Approvers',
        help='Optional. When set, only these users may approve, on top of '
             'belonging to the approver group.')
    approval_required = fields.Boolean(
        string='Approval Required', default=True,
        help='Uncheck to make this band auto-approved.')
    notify = fields.Boolean(string='Send Notification', default=True)

    @api.depends('document_type', 'amount_from', 'amount_to', 'approver_group_id')
    def _compute_name(self):
        labels = dict(APPROVAL_DOCUMENT_SELECTION)
        for rule in self:
            upper = ('%s' % rule.amount_to) if rule.amount_to else _('and above')
            rule.name = '%s: %s - %s (%s)' % (
                labels.get(rule.document_type, rule.document_type or ''),
                rule.amount_from, upper,
                rule.approver_group_id.name or _('unset'))

    @api.constrains('amount_from', 'amount_to')
    def _check_amounts(self):
        for rule in self:
            if rule.amount_from < 0 or rule.amount_to < 0:
                raise ValidationError(_('Approval amounts cannot be negative.'))
            if rule.amount_to and rule.amount_to < rule.amount_from:
                raise ValidationError(_(
                    '"Amount To" must be greater than or equal to "Amount From".'))

    @api.model
    def _get_rule(self, document_type, amount, company=None):
        """Return the approval band matching ``amount`` (SRS 60)."""
        company = company or self.env.company
        rules = self.search([
            ('document_type', '=', document_type),
            ('company_id', '=', company.id),
            ('active', '=', True),
        ], order='amount_from asc')
        for rule in rules:
            if amount >= rule.amount_from and (
                    not rule.amount_to or amount <= rule.amount_to):
                return rule
        return self.browse()

    @api.model
    def check_approver(self, document_type, amount, user=None, company=None):
        """Raise nothing, return ``(allowed, rule)`` for the given user."""
        user = user or self.env.user
        rule = self._get_rule(document_type, amount, company)
        if not rule:
            # No matrix configured -> fall back to the plain group check.
            return True, rule
        if not rule.approval_required:
            return True, rule
        if rule.approver_user_ids and user not in rule.approver_user_ids:
            return False, rule
        # ``groups_id`` already contains the implied groups, so a simple
        # membership test covers inherited privileges as well.
        return rule.approver_group_id in user.groups_id, rule
