# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwExportCosting(models.Model):
    _name = 'fw.export.costing'
    _description = 'Footwear Export Costing (FOB vs. Cost Analysis)'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Export Costing Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.export.costing') or 'New')
    buyer_order_id = fields.Many2one('fw.buyer.order', string='Buyer Order', required=True,
                                      tracking=True)
    style_costing_id = fields.Many2one('fw.style.costing', string='Style Cost Sheet',
                                        help="Optional link to a confirmed Style Cost Sheet to "
                                             "pull the Cut & Make cost per pair from.")

    currency_id = fields.Many2one(related='buyer_order_id.currency_id', string='Currency',
                                   store=True)

    order_qty = fields.Integer(string='Order Qty (Pairs)', related='buyer_order_id.total_qty',
                                store=True)
    fob_value = fields.Monetary(string='Total FOB Value', currency_field='currency_id')

    cm_cost_per_pair = fields.Monetary(string='Cut & Make Cost per Pair',
                                        currency_field='currency_id',
                                        help="Total manufacturing cost per pair, typically "
                                             "pulled from a Style Cost Sheet.")
    total_cm_cost = fields.Monetary(string='Total Cut & Make Cost', compute='_compute_costs',
                                     store=True, currency_field='currency_id')

    freight_cost = fields.Monetary(string='Freight Cost', currency_field='currency_id')
    insurance_cost = fields.Monetary(string='Insurance Cost', currency_field='currency_id')
    other_export_cost = fields.Monetary(string='Other Export Cost (Documentation/Commission)',
                                         currency_field='currency_id')

    total_export_cost = fields.Monetary(string='Total Cost', compute='_compute_costs',
                                         store=True, currency_field='currency_id')
    net_margin = fields.Monetary(string='Net Margin', compute='_compute_costs', store=True,
                                  currency_field='currency_id')
    net_margin_percent = fields.Float(string='Net Margin (%)', compute='_compute_costs',
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
                    'fw.export.costing') or 'New'
        return super().create(vals_list)

    @api.depends('order_qty', 'cm_cost_per_pair', 'freight_cost', 'insurance_cost',
                 'other_export_cost', 'fob_value')
    def _compute_costs(self):
        for rec in self:
            rec.total_cm_cost = (rec.order_qty or 0) * (rec.cm_cost_per_pair or 0.0)
            rec.total_export_cost = rec.total_cm_cost + (rec.freight_cost or 0.0) \
                + (rec.insurance_cost or 0.0) + (rec.other_export_cost or 0.0)
            rec.net_margin = (rec.fob_value or 0.0) - rec.total_export_cost
            rec.net_margin_percent = (rec.net_margin / rec.fob_value * 100.0) \
                if rec.fob_value else 0.0

    @api.constrains('fob_value', 'cm_cost_per_pair', 'freight_cost', 'insurance_cost',
                     'other_export_cost')
    def _check_non_negative(self):
        for rec in self:
            for field_name, label in [
                ('fob_value', 'FOB Value'), ('cm_cost_per_pair', 'Cut & Make Cost per Pair'),
                ('freight_cost', 'Freight Cost'), ('insurance_cost', 'Insurance Cost'),
                ('other_export_cost', 'Other Export Cost'),
            ]:
                if rec[field_name] < 0:
                    raise ValidationError("%s cannot be negative." % label)

    def action_pull_fob_from_order(self):
        for rec in self:
            rec.fob_value = rec.buyer_order_id.total_amount

    def action_pull_cm_from_costing(self):
        for rec in self:
            if rec.style_costing_id:
                rec.cm_cost_per_pair = rec.style_costing_id.total_cost

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
