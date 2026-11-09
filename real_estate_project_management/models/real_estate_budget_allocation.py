# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateBudgetAllocation(models.Model):
    """A single budget-head line within a Project Budget. Requisitions,
    Contractor Bills and (in later phases) Project Expenses commit
    against these lines, enforcing budget control per the spec's
    'never allow unauthorized overspending' rule.
    """
    _name = 'real.estate.budget.allocation'
    _description = 'Real Estate Budget Allocation'
    _rec_name = 'budget_head'
    _order = 'id'

    budget_id = fields.Many2one('real.estate.project.budget', string='Budget',
                                 required=True, ondelete='cascade')
    project_id = fields.Many2one(related='budget_id.project_id', store=True, readonly=True)
    budget_head = fields.Selection([
        ('land', 'Land'),
        ('construction', 'Construction'),
        ('civil', 'Civil'),
        ('structural', 'Structural'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('hvac', 'HVAC'),
        ('fire_safety', 'Fire Safety'),
        ('lift', 'Lift'),
        ('interior', 'Interior'),
        ('labour', 'Labour'),
        ('contractor', 'Contractor'),
        ('materials', 'Materials'),
        ('transportation', 'Transportation'),
        ('legal', 'Legal'),
        ('government_fees', 'Government Fees'),
        ('marketing', 'Marketing'),
        ('consultancy', 'Consultancy'),
        ('utilities', 'Utilities'),
        ('administration', 'Administration'),
        ('other', 'Other'),
    ], string='Budget Head', required=True)
    building_id = fields.Many2one('real.estate.building', string='Building',
                                   domain="[('project_id', '=', project_id)]")
    work_package_id = fields.Many2one('real.estate.work.package', string='Work Package',
                                       domain="[('project_id', '=', project_id)]")

    allocated_amount = fields.Monetary(string='Allocated Amount', required=True)
    committed_amount = fields.Monetary(string='Committed Amount', default=0.0, copy=False,
                                        help='Sum of approved requisitions/POs/contractor bills not yet invoiced.')
    actual_amount = fields.Monetary(string='Actual Amount', default=0.0, copy=False,
                                     help='Sum of posted expenses/invoices against this budget head.')
    remaining_amount = fields.Monetary(string='Remaining Amount', compute='_compute_remaining', store=True)
    variance_amount = fields.Monetary(string='Variance', compute='_compute_remaining', store=True)
    utilization_percentage = fields.Float(string='Utilization %', compute='_compute_remaining', store=True)

    allow_overspend = fields.Boolean(
        string='Allow Overspend (with approval)', default=False,
        help='If disabled, transactions that would exceed the remaining '
             'budget on this head are blocked outright. If enabled, they '
             'are allowed but flagged for higher approval elsewhere.')

    company_id = fields.Many2one(related='budget_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='budget_id.currency_id', readonly=True)

    @api.depends('allocated_amount', 'committed_amount', 'actual_amount')
    def _compute_remaining(self):
        for rec in self:
            rec.remaining_amount = rec.allocated_amount - rec.committed_amount - rec.actual_amount
            rec.variance_amount = rec.allocated_amount - rec.actual_amount
            rec.utilization_percentage = rec.allocated_amount and (
                (rec.committed_amount + rec.actual_amount) / rec.allocated_amount * 100.0) or 0.0

    def check_budget_availability(self, amount):
        """Raise if committing `amount` would exceed the remaining budget
        and overspend is not allowed on this line. Used by Requisition /
        Contractor Bill / Project Expense workflows in later phases."""
        self.ensure_one()
        projected_remaining = self.remaining_amount - amount
        if projected_remaining < 0 and not self.allow_overspend:
            raise UserError(
                'Budget Exceeded on "%s" (%s): requested %.2f, only %.2f '
                'remaining. Enable "Allow Overspend" on this budget line or '
                'reduce the request.' % (
                    self.budget_head, self.project_id.project_name,
                    amount, self.remaining_amount))
        return projected_remaining
