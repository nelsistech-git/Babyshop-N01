# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentStyleApprovalRule(models.Model):
    """Configurable Approval Rules master (SRS section 22 Lifecycle Controls —
    'Mandatory Approvals' per stage, section 25 Style Approval Workflow, and
    section 35 Menu Structure > Configuration > Approval Rules).

    Drives garment.style.action_generate_approvals_from_rules(): the matching
    rules (by Product Category, or generic rules with no category set) are
    used to auto-create the required garment.style.approval steps for a
    style, in sequence order."""
    _name = 'garment.style.approval.rule'
    _description = 'Garment Style Approval Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    style_category_id = fields.Many2one('garment.style.category', string='Product Category',
                                         help='Leave blank to apply this rule to every product category.')
    sequence = fields.Integer(default=10)
    approval_step = fields.Selection([
        ('designer', 'Designer'), ('design_manager', 'Design Manager'),
        ('merchandising_review', 'Merchandising Review'), ('sampling_review', 'Sampling Review'),
        ('qa_verification', 'QA Verification'), ('buyer_approval', 'Buyer Approval'),
    ], string='Approval Step', required=True)
    responsible_department = fields.Char(string='Responsible Department')
    is_mandatory = fields.Boolean(string='Mandatory', default=True)
    active = fields.Boolean(default=True)
