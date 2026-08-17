# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateDashboard(models.Model):
    """A live KPI summary. Deliberately built as plain computed fields on
    a normal model rather than a custom OWL app - per spec section 51's
    'Use OWL only where it provides meaningful dashboard functionality',
    a form view of computed fields plus standard Graph/Pivot views on the
    underlying models (see real_estate_dashboard_views.xml) covers every
    KPI and chart in the spec without introducing JS assets that can't be
    verified without a live Odoo instance.

    No records are ever meant to be saved: the action that opens this
    model always opens a fresh unsaved 'new record' form, so the KPIs
    are always computed from current data, never a stale snapshot."""
    _name = 'real.estate.dashboard'
    _description = 'Real Estate Management Dashboard'

    name = fields.Char(default='Management Dashboard')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    total_projects = fields.Integer(compute='_compute_kpis')
    active_projects = fields.Integer(compute='_compute_kpis')
    completed_projects = fields.Integer(compute='_compute_kpis')

    total_units = fields.Integer(compute='_compute_kpis')
    available_units = fields.Integer(compute='_compute_kpis')
    booked_units = fields.Integer(compute='_compute_kpis')
    sold_units = fields.Integer(compute='_compute_kpis')
    rented_units = fields.Integer(compute='_compute_kpis')

    total_budget = fields.Monetary(compute='_compute_kpis')
    actual_cost = fields.Monetary(compute='_compute_kpis')
    budget_utilization_percentage = fields.Float(compute='_compute_kpis')

    total_sales = fields.Monetary(compute='_compute_kpis')
    total_collection = fields.Monetary(compute='_compute_kpis')
    total_receivable = fields.Monetary(compute='_compute_kpis')
    total_overdue = fields.Monetary(compute='_compute_kpis')

    estimated_profit = fields.Monetary(compute='_compute_kpis')

    @api.depends('company_id')
    def _compute_kpis(self):
        Project = self.env['real.estate.project']
        Unit = self.env['real.estate.unit']
        Budget = self.env['real.estate.project.budget']
        Agreement = self.env['real.estate.sale.agreement']
        Collection = self.env['real.estate.collection']
        Installment = self.env['real.estate.installment']

        for rec in self:
            projects = Project.search([('company_id', '=', rec.company_id.id)])
            rec.total_projects = len(projects)
            rec.active_projects = len(projects.filtered(
                lambda p: p.state in ('construction', 'qc', 'ready')))
            rec.completed_projects = len(projects.filtered(lambda p: p.state == 'completed'))

            units = Unit.search([('company_id', '=', rec.company_id.id)])
            rec.total_units = len(units)
            rec.available_units = len(units.filtered(lambda u: u.status == 'available'))
            rec.booked_units = len(units.filtered(lambda u: u.status == 'booked'))
            rec.sold_units = len(units.filtered(lambda u: u.status == 'sold'))
            rec.rented_units = len(units.filtered(lambda u: u.status == 'rented'))

            budgets = Budget.search([('company_id', '=', rec.company_id.id)])
            rec.total_budget = sum(budgets.mapped('total_budget'))
            rec.actual_cost = sum(budgets.mapped('total_actual'))
            rec.budget_utilization_percentage = rec.total_budget and (
                rec.actual_cost / rec.total_budget * 100.0) or 0.0

            agreements = Agreement.search([
                ('company_id', '=', rec.company_id.id), ('state', 'in', ('active', 'completed'))])
            rec.total_sales = sum(agreements.mapped('net_price'))

            collections = Collection.search([
                ('company_id', '=', rec.company_id.id), ('state', '=', 'confirmed')])
            rec.total_collection = sum(collections.mapped('amount'))

            installments = Installment.search([('company_id', '=', rec.company_id.id)])
            rec.total_receivable = sum(installments.mapped('due_amount'))
            rec.total_overdue = sum(installments.filtered(
                lambda i: i.status == 'overdue').mapped('due_amount'))

            rec.estimated_profit = rec.total_sales - rec.actual_cost
