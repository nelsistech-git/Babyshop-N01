# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentCostCenter(models.Model):
    """Cost Center Management (SRS section 10) — garment.cost.center."""
    _name = 'garment.cost.center'
    _description = 'Garment Cost Center'
    _order = 'name'

    name = fields.Char(string='Cost Center Name', required=True)
    department = fields.Selection([
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('washing', 'Washing'), ('finishing', 'Finishing'),
        ('quality', 'Quality'), ('maintenance', 'Maintenance'), ('administration', 'Administration'),
    ], string='Department', required=True)
    factory = fields.Char(string='Factory')
    manager_id = fields.Many2one('res.users', string='Cost Center Manager')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    budget_ids = fields.One2many('garment.budget', 'cost_center_id', string='Budgets')
    expense_ids = fields.One2many('garment.expense', 'cost_center_id', string='Expenses')

    monthly_cost = fields.Monetary(string='Monthly Cost (actual)', compute='_compute_monthly_cost', store=True,
                                    currency_field='currency_id')
    monthly_output = fields.Float(string='Monthly Output (PCS)')
    cost_per_piece = fields.Monetary(string='Cost per Piece', compute='_compute_monthly_cost', store=True,
                                      currency_field='currency_id')
    active = fields.Boolean(default=True)

    @api.depends('expense_ids.amount', 'expense_ids.status', 'monthly_output')
    def _compute_monthly_cost(self):
        for rec in self:
            approved = rec.expense_ids.filtered(lambda e: e.status == 'approved')
            total = sum(approved.mapped('amount'))
            rec.monthly_cost = total
            rec.cost_per_piece = (total / rec.monthly_output) if rec.monthly_output else 0.0
