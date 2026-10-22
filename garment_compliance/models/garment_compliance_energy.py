# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Energy Management & Carbon Footprint (SRS1 secs. 35, 43-46, SRS2 secs.
57-58) — garment.compliance.energy. Carbon Emission = Energy Consumption
x Emission Factor (SRS1 sec. 44 formula).
"""
from odoo import api, fields, models


class GarmentComplianceEnergy(models.Model):
    _name = 'garment.compliance.energy'
    _description = 'Garment Compliance Energy / Carbon Record'
    _order = 'record_date desc'

    record_date = fields.Date(string='Record Month', default=fields.Date.context_today, required=True)
    electricity_kwh = fields.Float(string='Electricity (kWh)')
    gas_usage = fields.Float(string='Gas Usage (m³)')
    generator_fuel_liters = fields.Float(string='Generator Fuel (Liters)')
    solar_kwh = fields.Float(string='Solar Energy (kWh)')
    total_energy_kwh = fields.Float(string='Total Energy (kWh)', compute='_compute_totals', store=True)
    renewable_percentage = fields.Float(string='Renewable (%)', compute='_compute_totals', store=True)
    energy_cost = fields.Monetary(string='Total Energy Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    emission_factor = fields.Float(string='Emission Factor (Ton CO2/MWh)', default=0.5,
                                    help='Default grid emission factor for Bangladesh; adjust as needed.')
    carbon_emission_ton = fields.Float(string='Carbon Emission (Ton CO2)', compute='_compute_totals', store=True)

    @api.depends('electricity_kwh', 'gas_usage', 'generator_fuel_liters', 'solar_kwh', 'emission_factor')
    def _compute_totals(self):
        for rec in self:
            rec.total_energy_kwh = rec.electricity_kwh + rec.solar_kwh
            rec.renewable_percentage = (rec.solar_kwh / rec.total_energy_kwh * 100.0) if rec.total_energy_kwh else 0.0
            rec.carbon_emission_ton = (rec.electricity_kwh / 1000.0) * rec.emission_factor
