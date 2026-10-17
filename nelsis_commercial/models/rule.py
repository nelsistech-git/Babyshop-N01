# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import fields, models
from .constants import TRANSACTION_TYPES


class NelsisCommercialRule(models.Model):
    """Configurable, version-controlled compliance document matrix.
    No statutory requirement is hard-coded: every rule is entered and reviewed by the company."""
    _name = 'nelsis.commercial.rule'
    _description = 'Compliance Document Requirement'
    _inherit = ['mail.thread']
    _order = 'transaction_type, document_type_id'

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one('res.company', help="Leave empty to apply to all companies.")
    transaction_type = fields.Selection(
        TRANSACTION_TYPES, help="Leave empty to apply to every transaction type.", tracking=True)
    document_type_id = fields.Many2one('nelsis.commercial.document.type', required=True, tracking=True)
    requirement = fields.Selection(
        [('required', 'Required'), ('conditional', 'Conditional'), ('optional', 'Optional')],
        default='required', required=True, tracking=True,
        help="Only 'Required' rules block file progress. Conditional rules are shown for manual judgement.")
    source_reference = fields.Char(string='Official Rule / SRO Reference', tracking=True)
    source_url = fields.Char(string='Source URL')
    effective_date = fields.Date(tracking=True)
    amendment_status = fields.Selection(
        [('current', 'Current'), ('amended', 'Amended'), ('superseded', 'Superseded'), ('unverified', 'Unverified')],
        default='unverified', required=True, tracking=True)
    applicability = fields.Text(string='Applicability Criteria')
    verification_required = fields.Boolean(default=True)
    renewal_note = fields.Char(string='Expiry / Renewal Rule')
    department = fields.Char(string='Responsible Department')
    reviewed_by = fields.Many2one('res.users', readonly=True, copy=False)
    review_date = fields.Date(readonly=True, copy=False)
    legal_note = fields.Text(
        string='Interpretation Needing Confirmation',
        help="Flag legal interpretations to be confirmed by an authorized customs/compliance professional.")

    def action_mark_reviewed(self):
        self.write({'reviewed_by': self.env.user.id, 'review_date': fields.Date.context_today(self)})
