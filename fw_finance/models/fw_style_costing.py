# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwStyleCosting(models.Model):
    _name = 'fw.style.costing'
    _description = 'Footwear Style Cost Sheet'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Cost Sheet Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.style.costing') or 'New')
    style_id = fields.Many2one('fw.style', string='Style', required=True, tracking=True)
    bom_id = fields.Many2one('fw.bom.version', string='BOM Version',
                              domain="[('style_id', '=', style_id), ('state', '=', 'confirmed')]")
    line_balancing_id = fields.Many2one('fw.line.balancing', string='Line Balancing Reference',
                                         domain="[('style_id', '=', style_id)]")

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    material_cost = fields.Monetary(string='Material Cost (per Pair)', currency_field='currency_id')
    labor_rate_per_minute = fields.Monetary(string='Labor Rate (per SMV Minute)',
                                             currency_field='currency_id')
    labor_cost = fields.Monetary(string='Labor Cost (per Pair)', currency_field='currency_id')

    overhead_percent = fields.Float(string='Overhead (% of Labor)', default=30.0)
    overhead_cost = fields.Monetary(string='Overhead Cost (per Pair)', compute='_compute_overhead',
                                     store=True, currency_field='currency_id')

    other_cost = fields.Monetary(string='Other Cost (Packing/Commission/etc.)',
                                  currency_field='currency_id')

    total_cost = fields.Monetary(string='Total Cost (per Pair)', compute='_compute_totals',
                                  store=True, currency_field='currency_id')

    selling_price = fields.Monetary(string='Selling Price / FOB (per Pair)',
                                     currency_field='currency_id')
    profit_amount = fields.Monetary(string='Profit (per Pair)', compute='_compute_totals',
                                     store=True, currency_field='currency_id')
    profit_margin_percent = fields.Float(string='Margin (%)', compute='_compute_totals',
                                          store=True)

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
                    'fw.style.costing') or 'New'
        return super().create(vals_list)

    @api.depends('labor_cost', 'overhead_percent')
    def _compute_overhead(self):
        for rec in self:
            rec.overhead_cost = (rec.labor_cost or 0.0) * (rec.overhead_percent or 0.0) / 100.0

    @api.depends('material_cost', 'labor_cost', 'overhead_cost', 'other_cost', 'selling_price')
    def _compute_totals(self):
        for rec in self:
            rec.total_cost = (rec.material_cost or 0.0) + (rec.labor_cost or 0.0) \
                + (rec.overhead_cost or 0.0) + (rec.other_cost or 0.0)
            rec.profit_amount = (rec.selling_price or 0.0) - rec.total_cost
            rec.profit_margin_percent = (rec.profit_amount / rec.selling_price * 100.0) \
                if rec.selling_price else 0.0

    @api.constrains('material_cost', 'labor_cost', 'other_cost', 'selling_price',
                     'labor_rate_per_minute')
    def _check_non_negative(self):
        for rec in self:
            for field_name, label in [
                ('material_cost', 'Material Cost'), ('labor_cost', 'Labor Cost'),
                ('other_cost', 'Other Cost'), ('selling_price', 'Selling Price'),
                ('labor_rate_per_minute', 'Labor Rate per Minute'),
            ]:
                if rec[field_name] < 0:
                    raise ValidationError("%s cannot be negative." % label)

    def action_pull_material_cost(self):
        for rec in self:
            if not rec.bom_id:
                raise UserError("Please select a confirmed BOM Version first.")
            rec.material_cost = rec.bom_id.total_cost

    def action_pull_labor_cost(self):
        for rec in self:
            if not rec.line_balancing_id:
                raise UserError("Please select a Line Balancing reference first.")
            rec.labor_cost = rec.line_balancing_id.total_smv * (rec.labor_rate_per_minute or 0.0)

    def action_pull_selling_price(self):
        for rec in self:
            rec.selling_price = rec.style_id.last_price

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
