# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentBudget(models.Model):
    """Budget Management + Approval Workflow (SRS sections 11-12) —
    garment.budget."""
    _name = 'garment.budget'
    _description = 'Garment Budget'
    _inherit = ['mail.thread']
    _order = 'period_start desc'

    name = fields.Char(string='Budget Name', required=True)
    budget_type = fields.Selection([
        ('annual', 'Annual Budget'), ('monthly', 'Monthly Budget'),
        ('department', 'Department Budget'), ('production', 'Production Budget'),
    ], string='Budget Type', required=True)
    cost_center_id = fields.Many2one('garment.cost.center', string='Cost Center')
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    budgeted_amount = fields.Monetary(string='Budgeted Amount', required=True, currency_field='currency_id')
    actual_amount = fields.Monetary(string='Actual Amount', compute='_compute_actual', store=True,
                                     currency_field='currency_id')
    remaining_amount = fields.Monetary(string='Remaining Amount', compute='_compute_actual', store=True,
                                        currency_field='currency_id')
    utilization_pct = fields.Float(string='Utilization %', compute='_compute_actual', store=True)

    # Variance Analysis (SRS section 30 "Budget vs Actual Cost", Module 20; and
    # "Cost Variance Analysis" section 46, Module 37 — at the cost-center/budget
    # level. Order/style-level material/labor/overhead variance is already owned
    # by garment_costing's garment.cost.variance model; this is the budget-level
    # counterpart, kept distinct from utilization_pct (actual/budget) since
    # variance is signed (actual - budget) and carries a narrative reason.
    variance_amount = fields.Monetary(string='Variance (Actual - Budget)', compute='_compute_actual', store=True,
                                       currency_field='currency_id')
    variance_pct = fields.Float(string='Variance %', compute='_compute_actual', store=True)
    variance_reason = fields.Text(string='Variance Reason', help='e.g. "Higher Fabric Cost" — narrative explanation '
                                                                   'for a significant budget variance.')

    status = fields.Selection([
        ('draft', 'Department Request'), ('finance_review', 'Finance Review'),
        ('management_approval', 'Management Approval'), ('allocated', 'Budget Allocation'),
        ('monitoring', 'Expense Monitoring'), ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('cost_center_id.expense_ids.amount', 'cost_center_id.expense_ids.status',
                 'cost_center_id.expense_ids.expense_date', 'period_start', 'period_end', 'budgeted_amount')
    def _compute_actual(self):
        for rec in self:
            expenses = rec.cost_center_id.expense_ids.filtered(
                lambda e: e.status == 'approved' and rec.period_start <= e.expense_date <= rec.period_end
            ) if rec.cost_center_id and rec.period_start and rec.period_end else rec.cost_center_id.expense_ids.browse()
            actual = sum(expenses.mapped('amount'))
            rec.actual_amount = actual
            rec.remaining_amount = (rec.budgeted_amount or 0.0) - actual
            rec.utilization_pct = (actual / rec.budgeted_amount * 100.0) if rec.budgeted_amount else 0.0
            rec.variance_amount = actual - (rec.budgeted_amount or 0.0)
            rec.variance_pct = (rec.variance_amount / rec.budgeted_amount * 100.0) if rec.budgeted_amount else 0.0

    def action_next_stage(self):
        flow = ['draft', 'finance_review', 'management_approval', 'allocated', 'monitoring', 'closed']
        for rec in self:
            idx = flow.index(rec.status)
            if idx < len(flow) - 1:
                rec.status = flow[idx + 1]
