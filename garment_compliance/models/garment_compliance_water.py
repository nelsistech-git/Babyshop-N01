# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Water Management & Effluent Treatment Plant (ETP) (SRS1 secs. 36, 47-48,
SRS2 secs. 55-56) — garment.compliance.water.
"""
from odoo import fields, models


class GarmentComplianceWater(models.Model):
    _name = 'garment.compliance.water'
    _description = 'Garment Compliance Water / ETP Record'
    _order = 'record_date desc'

    record_date = fields.Date(string='Record Date', default=fields.Date.context_today, required=True)
    department_id = fields.Many2one('garment.hr.department', string='Department')
    source = fields.Selection([
        ('ground_water', 'Ground Water'), ('supply_water', 'Supply Water'), ('treatment_plant', 'Treatment Plant'),
    ], string='Source', default='supply_water')
    consumption_m3 = fields.Float(string='Consumption (m³)')
    recycled_percentage = fields.Float(string='Recycled (%)')
    discharge_m3 = fields.Float(string='Discharge (m³)')

    is_etp_test = fields.Boolean(string='ETP Water Quality Test')
    etp_ph_level = fields.Float(string='pH Level')
    etp_cod = fields.Float(string='COD (mg/L)')
    etp_bod = fields.Float(string='BOD (mg/L)')
    etp_tds = fields.Float(string='TDS (mg/L)')
    tested_by = fields.Char(string='Tested By')
    quality_status = fields.Selection([
        ('approved', 'Approved'), ('rejected', 'Rejected'), ('pending', 'Pending'),
    ], string='Quality Status', default='pending')
    notes = fields.Text(string='Notes')
