# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Building Safety Management System (SRS2 secs. 38-42) —
garment.compliance.building / garment.compliance.building.inspection.
Structural, electrical and generator safety of the factory building(s),
kept separate from garment.warehouse (a stock-keeping structure) since a
factory building can host several warehouses/production floors.
"""
from odoo import fields, models


class GarmentComplianceBuilding(models.Model):
    _name = 'garment.compliance.building'
    _description = 'Garment Compliance Factory Building'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Building Name', required=True)
    address = fields.Char(string='Address')
    warehouse_ids = fields.Many2many('garment.warehouse', string='Warehouses / Floors Housed')
    floors = fields.Integer(string='Number of Floors')
    worker_capacity = fields.Integer(string='Worker Capacity')
    approval_status = fields.Selection([
        ('approved', 'Approved'), ('conditional', 'Conditional'), ('pending', 'Pending'), ('not_approved', 'Not Approved'),
    ], string='Approval Status', default='pending', tracking=True)
    approval_certificate_id = fields.Many2one('garment.compliance.certificate', string='Approval Certificate')
    inspection_ids = fields.One2many('garment.compliance.building.inspection', 'building_id', string='Inspections')
    inspection_count = fields.Integer(compute='_compute_inspection_count')
    active = fields.Boolean(default=True)

    def _compute_inspection_count(self):
        for rec in self:
            rec.inspection_count = len(rec.inspection_ids)


class GarmentComplianceBuildingInspection(models.Model):
    _name = 'garment.compliance.building.inspection'
    _description = 'Garment Building / Structural / Electrical Inspection'
    _order = 'inspection_date desc'

    building_id = fields.Many2one('garment.compliance.building', string='Building', required=True, ondelete='cascade')
    inspection_type = fields.Selection([
        ('structural', 'Structural Inspection'), ('electrical', 'Electrical Safety'), ('generator', 'Generator & Power Safety'),
    ], string='Inspection Type', required=True, default='structural')
    inspection_date = fields.Date(string='Inspection Date', default=fields.Date.context_today)
    inspector = fields.Char(string='Engineer / Inspector')
    condition = fields.Selection([
        ('good', 'Good'), ('fair', 'Fair'), ('poor', 'Poor'),
    ], string='Condition')
    findings = fields.Text(string='Findings / Engineer Report')
    corrective_action = fields.Text(string='Corrective Action')
    next_inspection_date = fields.Date(string='Next Inspection Date')
    status = fields.Selection([
        ('open', 'Open'), ('closed', 'Closed'),
    ], string='Status', default='open')
