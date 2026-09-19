# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwEfficiencyReport(models.Model):
    _name = 'fw.efficiency.report'
    _description = 'Footwear Daily Line Efficiency Report'
    _order = 'date desc'

    name = fields.Char(string='Report Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.efficiency.report') or 'New')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    factory_id = fields.Many2one('fw.factory', string='Factory', required=True)
    production_line_id = fields.Many2one('fw.production.line', string='Production Line',
                                          required=True, domain="[('factory_id', '=', factory_id)]")
    style_id = fields.Many2one('fw.style', string='Style')
    balancing_id = fields.Many2one('fw.line.balancing', string='Line Balancing Reference',
                                    domain="[('production_line_id', '=', production_line_id)]")

    smv = fields.Float(string='SMV (min)', required=True, digits=(8, 4),
                        help="Standard Minute Value used as the efficiency benchmark for "
                             "this line/style on this date.")
    working_minutes = fields.Float(string='Working Minutes', default=480.0)
    manpower_present = fields.Integer(string='Manpower Present', required=True, default=0)
    produced_qty = fields.Integer(string='Produced Qty (Pairs)', required=True, default=0)

    @api.constrains('smv', 'working_minutes', 'manpower_present', 'produced_qty')
    def _check_non_negative(self):
        for rec in self:
            for field_name, label in [
                ('smv', 'SMV'), ('working_minutes', 'Working Minutes'),
                ('manpower_present', 'Manpower Present'), ('produced_qty', 'Produced Qty'),
            ]:
                if rec[field_name] < 0:
                    raise ValidationError("%s cannot be negative." % label)

    earned_minutes = fields.Float(string='Earned Minutes', compute='_compute_efficiency',
                                   store=True)
    available_minutes = fields.Float(string='Available Minutes', compute='_compute_efficiency',
                                      store=True)
    efficiency_percent = fields.Float(string='Efficiency (%)', compute='_compute_efficiency',
                                       store=True)

    remarks = fields.Char(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.efficiency.report') or 'New'
        return super().create(vals_list)

    @api.onchange('balancing_id')
    def _onchange_balancing_id(self):
        if self.balancing_id:
            self.smv = self.balancing_id.total_smv
            if not self.style_id:
                self.style_id = self.balancing_id.style_id

    @api.depends('produced_qty', 'smv', 'working_minutes', 'manpower_present')
    def _compute_efficiency(self):
        for rec in self:
            rec.earned_minutes = (rec.produced_qty or 0) * (rec.smv or 0.0)
            rec.available_minutes = (rec.working_minutes or 0.0) * (rec.manpower_present or 0)
            rec.efficiency_percent = (rec.earned_minutes / rec.available_minutes * 100.0) \
                if rec.available_minutes else 0.0
