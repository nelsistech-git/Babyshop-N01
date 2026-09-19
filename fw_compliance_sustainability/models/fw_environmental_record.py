# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwEnvironmentalRecord(models.Model):
    _name = 'fw.environmental.record'
    _description = 'Footwear Factory Environmental & Sustainability Record'
    _inherit = ['mail.thread']
    _order = 'period_end desc'

    name = fields.Char(string='Record Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.environmental.record') or 'New')
    factory_id = fields.Many2one('fw.factory', string='Factory', required=True, tracking=True)
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)

    water_consumption_m3 = fields.Float(string='Water Consumption (m³)')
    energy_consumption_kwh = fields.Float(string='Energy Consumption (kWh)')
    co2_emission_tons = fields.Float(string='CO2 Emission (Tons)')

    waste_generated_kg = fields.Float(string='Waste Generated (kg)')
    waste_recycled_kg = fields.Float(string='Waste Recycled (kg)')
    waste_recycled_percent = fields.Float(string='Waste Recycled (%)',
                                           compute='_compute_waste_percent', store=True)

    chemical_incident_count = fields.Integer(string='Chemical Incident Count', default=0)

    total_production_qty = fields.Integer(string='Total Production Qty (Pairs)',
                                           help="Optional - enter to see resource use per pair.")
    water_per_pair_liters = fields.Float(string='Water per Pair (Liters)',
                                          compute='_compute_per_pair', store=True)
    energy_per_pair_kwh = fields.Float(string='Energy per Pair (kWh)',
                                        compute='_compute_per_pair', store=True)

    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.environmental.record') or 'New'
        return super().create(vals_list)

    @api.constrains('period_start', 'period_end')
    def _check_dates(self):
        for rec in self:
            if rec.period_start and rec.period_end and rec.period_start > rec.period_end:
                raise ValidationError("Period Start cannot be after Period End.")

    @api.depends('waste_generated_kg', 'waste_recycled_kg')
    def _compute_waste_percent(self):
        for rec in self:
            rec.waste_recycled_percent = (
                rec.waste_recycled_kg / rec.waste_generated_kg * 100.0
            ) if rec.waste_generated_kg else 0.0

    @api.depends('water_consumption_m3', 'energy_consumption_kwh', 'total_production_qty')
    def _compute_per_pair(self):
        for rec in self:
            if rec.total_production_qty:
                rec.water_per_pair_liters = (
                    rec.water_consumption_m3 * 1000.0) / rec.total_production_qty
                rec.energy_per_pair_kwh = rec.energy_consumption_kwh / rec.total_production_qty
            else:
                rec.water_per_pair_liters = 0.0
                rec.energy_per_pair_kwh = 0.0
