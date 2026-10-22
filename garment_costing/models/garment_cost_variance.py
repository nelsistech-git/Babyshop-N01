# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentCostVariance(models.Model):
    """Estimated vs Actual Cost Analysis (SRS sections 25-26) —
    garment.cost.variance."""
    _name = 'garment.cost.variance'
    _description = 'Garment Cost Variance'
    _order = 'sequence'

    costing_id = fields.Many2one('garment.costing', string='Costing', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    variance_type = fields.Selection([
        ('material', 'Material Variance'), ('labor', 'Labor Variance'), ('overhead', 'Overhead Variance'),
    ], string='Variance Type', required=True)
    cause = fields.Selection([
        ('price_change', 'Price Change'), ('consumption_difference', 'Consumption Difference'),
        ('efficiency', 'Efficiency'), ('overtime', 'Overtime'), ('production_delay', 'Production Delay'),
        ('utility_cost', 'Utility Cost'), ('factory_expense', 'Factory Expense'), ('other', 'Other'),
    ], string='Cause')
    estimated_cost = fields.Monetary(string='Estimated Cost', currency_field='currency_id')
    actual_cost = fields.Monetary(string='Actual Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='costing_id.currency_id', store=True)
    variance_amount = fields.Monetary(string='Variance Amount', compute='_compute_variance', store=True,
                                       currency_field='currency_id')
    variance_pct = fields.Float(string='Variance %', compute='_compute_variance', store=True)
    notes = fields.Text(string='Notes')

    @api.depends('estimated_cost', 'actual_cost')
    def _compute_variance(self):
        for rec in self:
            rec.variance_amount = (rec.actual_cost or 0.0) - (rec.estimated_cost or 0.0)
            rec.variance_pct = (rec.variance_amount / rec.estimated_cost * 100.0) if rec.estimated_cost else 0.0
