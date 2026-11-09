# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateProjectProfitabilityLink(models.Model):
    """Phase 10: profitability KPIs for the Project, reusing
    total_sales_value (Phase 5) and each Budget's total_actual (Phase 3)
    rather than introducing a separate cost-tracking model."""
    _inherit = 'real.estate.project'

    rental_income = fields.Monetary(string='Rental Income', compute='_compute_profitability')
    total_revenue = fields.Monetary(string='Total Revenue', compute='_compute_profitability')
    total_actual_cost = fields.Monetary(string='Total Actual Cost', compute='_compute_profitability')
    gross_profit = fields.Monetary(string='Gross Profit', compute='_compute_profitability')
    profit_margin_percentage = fields.Float(string='Profit Margin %', compute='_compute_profitability')

    @api.depends('sale_agreement_ids.net_price', 'sale_agreement_ids.state', 'budget_ids.total_actual')
    def _compute_profitability(self):
        for rec in self:
            rental_collections = self.env['real.estate.collection'].search([
                ('project_id', '=', rec.id),
                ('rental_agreement_id', '!=', False),
                ('state', '=', 'confirmed'),
            ])
            rec.rental_income = sum(rental_collections.mapped('amount'))
            rec.total_revenue = rec.total_sales_value + rec.rental_income
            rec.total_actual_cost = sum(rec.budget_ids.mapped('total_actual'))
            rec.gross_profit = rec.total_revenue - rec.total_actual_cost
            rec.profit_margin_percentage = rec.total_revenue and (
                rec.gross_profit / rec.total_revenue * 100.0) or 0.0
