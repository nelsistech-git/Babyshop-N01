# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwFactoryCosting(models.Model):
    _name = 'fw.factory.costing'
    _description = 'Footwear Factory Periodic Costing'
    _inherit = ['mail.thread']
    _order = 'period_end desc'

    name = fields.Char(string='Costing Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.factory.costing') or 'New')
    factory_id = fields.Many2one('fw.factory', string='Factory', required=True, tracking=True)
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    total_production_qty = fields.Integer(string='Total Production Qty (Pairs)', default=0,
                                           help="Total finished pairs produced in the period. "
                                                "Use 'Pull Production Qty' to auto-fetch "
                                                "completed Production Orders whose Planned "
                                                "Finish date falls in the period, or enter "
                                                "manually.")
    total_material_cost = fields.Monetary(string='Total Material Cost', currency_field='currency_id')
    total_labor_cost = fields.Monetary(string='Total Labor Cost', currency_field='currency_id')
    total_overhead_cost = fields.Monetary(string='Total Overhead Cost', currency_field='currency_id')

    expense_line_ids = fields.One2many('fw.factory.costing.expense', 'costing_id',
                                        string='Other Expenses')
    total_other_expense = fields.Monetary(string='Total Other Expenses',
                                           compute='_compute_totals', store=True,
                                           currency_field='currency_id')

    total_cost = fields.Monetary(string='Grand Total Cost', compute='_compute_totals',
                                  store=True, currency_field='currency_id')
    cost_per_pair = fields.Monetary(string='Cost per Pair', compute='_compute_totals',
                                     store=True, currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.factory.costing') or 'New'
        return super().create(vals_list)

    @api.depends('total_material_cost', 'total_labor_cost', 'total_overhead_cost',
                 'expense_line_ids.amount', 'total_production_qty')
    def _compute_totals(self):
        for rec in self:
            rec.total_other_expense = sum(rec.expense_line_ids.mapped('amount'))
            rec.total_cost = (rec.total_material_cost or 0.0) + (rec.total_labor_cost or 0.0) \
                + (rec.total_overhead_cost or 0.0) + rec.total_other_expense
            rec.cost_per_pair = (rec.total_cost / rec.total_production_qty) \
                if rec.total_production_qty else 0.0

    def action_pull_production_qty(self):
        for rec in self:
            if not rec.period_start or not rec.period_end:
                raise UserError("Please set both Period Start and Period End first.")
            production_orders = self.env['fw.production.order'].search([
                ('factory_id', '=', rec.factory_id.id),
                ('state', '=', 'completed'),
                ('date_planned_finish', '>=', rec.period_start),
                ('date_planned_finish', '<=', rec.period_end),
            ])
            rec.total_production_qty = sum(production_orders.mapped('finished_qty'))

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    @api.constrains('total_production_qty', 'total_material_cost', 'total_labor_cost',
                     'total_overhead_cost')
    def _check_non_negative(self):
        for rec in self:
            for field_name, label in [
                ('total_production_qty', 'Total Production Qty'),
                ('total_material_cost', 'Total Material Cost'),
                ('total_labor_cost', 'Total Labor Cost'),
                ('total_overhead_cost', 'Total Overhead Cost'),
            ]:
                if rec[field_name] < 0:
                    raise ValidationError("%s cannot be negative." % label)


class FwFactoryCostingExpense(models.Model):
    _name = 'fw.factory.costing.expense'
    _description = 'Factory Costing Other Expense Line'
    _order = 'id'

    costing_id = fields.Many2one('fw.factory.costing', string='Factory Costing', required=True,
                                  ondelete='cascade')
    expense_type = fields.Selection([
        ('utility', 'Utility (Electricity/Gas/Water)'),
        ('rent', 'Rent'),
        ('admin_salary', 'Admin/Management Salary'),
        ('maintenance', 'Maintenance'),
        ('transport', 'Transport'),
        ('other', 'Other'),
    ], string='Expense Type', required=True, default='other')
    description = fields.Char(string='Description')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one(related='costing_id.currency_id', string='Currency', store=True)

    @api.constrains('amount')
    def _check_amount_non_negative(self):
        for rec in self:
            if rec.amount < 0:
                raise ValidationError("Expense amount cannot be negative.")
