# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Waste Management System (SRS1 sec. 39, SRS2 secs. 53-54) —
garment.compliance.waste. Generated -> Collection -> Storage ->
Recycling/Disposal workflow.
"""
from odoo import fields, models


class GarmentComplianceWaste(models.Model):
    _name = 'garment.compliance.waste'
    _description = 'Garment Compliance Waste Record'
    _order = 'record_date desc'

    record_date = fields.Date(string='Record Date', default=fields.Date.context_today, required=True)
    waste_type = fields.Selection([
        ('fabric', 'Fabric Waste'), ('plastic', 'Plastic Waste'), ('paper', 'Paper Waste'),
        ('chemical', 'Chemical Waste'), ('metal', 'Metal Waste'), ('hazardous', 'Hazardous Waste'),
    ], string='Waste Type', required=True)
    department_id = fields.Many2one('garment.hr.department', string='Department')
    quantity = fields.Float(string='Quantity')
    uom = fields.Char(string='Unit', default='KG')
    disposal_method = fields.Selection([
        ('recycled', 'Recycled'), ('reused', 'Reused'), ('incinerated', 'Incinerated'),
        ('landfill', 'Landfill'), ('hazardous_disposal', 'Certified Hazardous Disposal'),
    ], string='Disposal Method')
    disposal_vendor = fields.Char(string='Disposal / Recycling Vendor')
    status = fields.Selection([
        ('generated', 'Generated'), ('collected', 'Collected'), ('stored', 'Stored'), ('disposed', 'Disposed / Recycled'),
    ], string='Status', default='generated')
    notes = fields.Text(string='Notes')
