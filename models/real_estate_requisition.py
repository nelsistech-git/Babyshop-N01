# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateRequisition(models.Model):
    """A site request for materials. Approved requisitions are the entry
    point into standard Odoo Purchase (RFQ/PO creation is a later-phase
    wizard, per the spec's 'do not duplicate Odoo Purchase' rule - this
    phase models the requisition itself and its approval/budget-check
    workflow only)."""
    _name = 'real.estate.requisition'
    _description = 'Real Estate Material Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Requisition Number', copy=False, tracking=True,
                        default='New', readonly=True)
    project_id = fields.Many2one('real.estate.project', string='Project',
                                  required=True, tracking=True, ondelete='restrict')
    building_id = fields.Many2one('real.estate.building', string='Building',
                                   domain="[('project_id', '=', project_id)]")
    work_package_id = fields.Many2one('real.estate.work.package', string='Work Package',
                                       domain="[('project_id', '=', project_id)]")
    site = fields.Char(string='Site')

    requester_id = fields.Many2one('res.users', string='Requester',
                                    default=lambda self: self.env.user, tracking=True)
    request_date = fields.Date(string='Request Date', default=fields.Date.context_today)
    required_date = fields.Date(string='Required Date')
    priority = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent'),
    ], string='Priority', default='medium')

    budget_allocation_id = fields.Many2one('real.estate.budget.allocation', string='Budget Head',
                                            domain="[('project_id', '=', project_id)]")
    line_ids = fields.One2many('real.estate.requisition.line', 'requisition_id',
                                string='Requisition Lines')
    estimated_cost = fields.Monetary(string='Estimated Cost', compute='_compute_estimated_cost', store=True)
    reason = fields.Text(string='Reason')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_requisition_ir_attachment_rel',
        'requisition_id', 'attachment_id', string='Attachments')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('pm_approval', 'Project Manager Approval'),
        ('budget_approval', 'Budget Approval'),
        ('procurement', 'Procurement'),
        ('purchase', 'Purchase'),
        ('received', 'Received'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ], string='State', default='draft', tracking=True, required=True, copy=False)

    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.depends('line_ids.estimated_amount')
    def _compute_estimated_cost(self):
        for rec in self:
            rec.estimated_cost = sum(rec.line_ids.mapped('estimated_amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.requisition') or 'New'
        return super().create(vals_list)

    def _require_state(self, expected):
        for rec in self:
            if rec.state != expected:
                raise UserError('Requisition "%s" must be in state "%s" for this '
                                 'action (currently "%s").' % (rec.name, expected, rec.state))

    def action_submit(self):
        self._require_state('draft')
        self.write({'state': 'submitted'})

    def action_pm_approve(self):
        self._require_state('submitted')
        self.write({'state': 'pm_approval'})

    def action_budget_approve(self):
        """Enforce budget control before releasing to procurement."""
        self._require_state('pm_approval')
        for rec in self:
            if rec.budget_allocation_id:
                rec.budget_allocation_id.check_budget_availability(rec.estimated_cost)
                rec.budget_allocation_id.committed_amount += rec.estimated_cost
        self.write({'state': 'budget_approval'})

    def action_send_to_procurement(self):
        self._require_state('budget_approval')
        self.write({'state': 'procurement'})

    def action_mark_purchased(self):
        self._require_state('procurement')
        self.write({'state': 'purchase'})

    def action_mark_received(self):
        self._require_state('purchase')
        self.write({'state': 'received'})

    def action_complete(self):
        self._require_state('received')
        self.write({'state': 'completed'})

    def action_reject(self):
        for rec in self:
            if rec.state in ('completed', 'rejected'):
                raise UserError('This requisition cannot be rejected from its current state.')
        self.write({'state': 'rejected'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
