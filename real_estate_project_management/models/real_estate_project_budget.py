# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateProjectBudget(models.Model):
    """The overall approved budget envelope for a project, broken down
    into category lines via real.estate.budget.allocation."""
    _name = 'real.estate.project.budget'
    _description = 'Real Estate Project Budget'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Budget Number', copy=False, tracking=True,
                        default='New', readonly=True)
    project_id = fields.Many2one('real.estate.project', string='Project',
                                  required=True, tracking=True, ondelete='restrict')
    fiscal_year = fields.Char(string='Fiscal Year', help='e.g. 2026 or 2026-2027')
    budget_date = fields.Date(string='Budget Date', default=fields.Date.context_today)
    budget_manager_id = fields.Many2one('res.users', string='Budget Manager',
                                         default=lambda self: self.env.user)

    allocation_ids = fields.One2many('real.estate.budget.allocation', 'budget_id',
                                      string='Budget Allocations')
    total_budget = fields.Monetary(string='Total Budget', compute='_compute_totals', store=True)
    total_committed = fields.Monetary(string='Total Committed', compute='_compute_totals', store=True)
    total_actual = fields.Monetary(string='Total Actual', compute='_compute_totals', store=True)
    total_remaining = fields.Monetary(string='Total Remaining', compute='_compute_totals', store=True)
    utilization_percentage = fields.Float(string='Utilization %', compute='_compute_totals', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='State', default='draft', tracking=True, required=True, copy=False)

    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Budget Number must be unique per company.'),
    ]

    @api.depends('allocation_ids.allocated_amount', 'allocation_ids.committed_amount',
                 'allocation_ids.actual_amount')
    def _compute_totals(self):
        for rec in self:
            allocated = sum(rec.allocation_ids.mapped('allocated_amount'))
            committed = sum(rec.allocation_ids.mapped('committed_amount'))
            actual = sum(rec.allocation_ids.mapped('actual_amount'))
            rec.total_budget = allocated
            rec.total_committed = committed
            rec.total_actual = actual
            rec.total_remaining = allocated - committed - actual
            rec.utilization_percentage = allocated and ((committed + actual) / allocated * 100.0) or 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.project.budget') or 'New'
        return super().create(vals_list)

    def _require_state(self, expected):
        for rec in self:
            if rec.state != expected:
                raise UserError('Budget "%s" must be in state "%s" for this action '
                                 '(currently "%s").' % (rec.name, expected, rec.state))

    def action_submit(self):
        self._require_state('draft')
        self.write({'state': 'submitted'})

    def action_approve(self):
        self._require_state('submitted')
        self.write({'state': 'approved'})

    def action_activate(self):
        self._require_state('approved')
        self.write({'state': 'active'})

    def action_close(self):
        for rec in self:
            if rec.state not in ('active', 'approved'):
                raise UserError('Only active or approved budgets can be closed.')
        self.write({'state': 'closed'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
