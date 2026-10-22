# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentDocumentApprovalWorkflow(models.Model):
    """Generic, configurable multi-step approval workflow TEMPLATE (SRS
    sections 14-16, 27-28). This is the reusable "route for approval"
    engine: any other module can look up a workflow by ``code`` through
    ``get_matching_workflow()`` below, assign it to a ``garment.document``'s
    ``workflow_id`` and call ``action_submit_for_approval()`` — without
    garment_document_management ever depending on that module."""
    _name = 'garment.document.approval.workflow'
    _description = 'Approval Workflow Template'
    _order = 'sequence, name'

    name = fields.Char(string='Workflow Name', required=True)
    code = fields.Char(string='Code', required=True,
                        help='Stable technical code other modules use to look up this workflow, '
                             'e.g. "buyer_contract_approval".')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    approval_type = fields.Selection([
        ('sequential', 'Sequential — one step after another'),
        ('parallel', 'Parallel — all steps at once'),
    ], string='Approval Type', default='sequential', required=True)
    category_id = fields.Many2one('garment.document.category', string='Applies To Category')
    applies_to_model_id = fields.Many2one('ir.model', string='Applies To Model',
                                           help='Optional: restrict this workflow to approval '
                                                'requests raised against this target model.')
    min_amount = fields.Monetary(string='Applies From Amount', currency_field='currency_id',
                                  help='Dynamic rule (SRS section 28): leave 0 to always apply, '
                                       'or set a threshold so this workflow is only offered above it, '
                                       'e.g. Director approval required only if > 10,00,000 BDT.')
    max_amount = fields.Monetary(string='Applies Up To Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    requires_signature = fields.Boolean(string='Requires E-Signature on Final Step')
    step_ids = fields.One2many('garment.document.approval.workflow.step', 'workflow_id',
                                string='Approval Steps')
    step_count = fields.Integer(compute='_compute_step_count')
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'A workflow with this code already exists!'),
    ]

    def _compute_step_count(self):
        for rec in self:
            rec.step_count = len(rec.step_ids)

    @api.model
    def get_matching_workflow(self, code=False, res_model=False, amount=0.0):
        """Generic lookup ANY module can call to resolve the applicable
        workflow for a document it is about to submit (SRS section 28 —
        Dynamic Approval Rules driven by amount / document type / model):

            workflow = self.env['garment.document.approval.workflow'].get_matching_workflow(
                code='buyer_contract_approval', amount=contract_value)
            document.write({'workflow_id': workflow.id})
            document.action_submit_for_approval()

        Returns an empty recordset if nothing matches."""
        domain = [('active', '=', True)]
        if code:
            domain.append(('code', '=', code))
        if res_model:
            domain += ['|', ('applies_to_model_id.model', '=', res_model), ('applies_to_model_id', '=', False)]
        for workflow in self.search(domain, order='sequence'):
            if workflow.min_amount and amount < workflow.min_amount:
                continue
            if workflow.max_amount and amount > workflow.max_amount:
                continue
            return workflow
        return self.browse()


class GarmentDocumentApprovalWorkflowStep(models.Model):
    """One step of an approval workflow template (SRS section 15 —
    Single / Multi-Level / Sequential / Parallel Approval)."""
    _name = 'garment.document.approval.workflow.step'
    _description = 'Approval Workflow Step'
    _order = 'workflow_id, sequence'

    workflow_id = fields.Many2one('garment.document.approval.workflow', string='Workflow',
                                   required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Step Name', required=True)
    approver_group_id = fields.Many2one('res.groups', string='Approver Group',
                                         help='Any user in this group may action this step.')
    approver_user_id = fields.Many2one('res.users', string='Specific Approver',
                                        help='If set, only this user may action this step '
                                             '(overrides the group).')
    requires_signature = fields.Boolean(string='Requires E-Signature')
    is_mandatory = fields.Boolean(string='Mandatory', default=True)
