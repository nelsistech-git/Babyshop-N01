# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Maintenance Checklist Management (Maintenance & Asset Mgmt SRS sec. 14,
CMMS SRS sec. 12) — reusable, equipment-type-specific checklist
templates (e.g. Sewing Machine Checklist, Generator Checklist). Lines
are copied onto a Work Order at creation time and ticked off there,
mirroring the Quality module's Checkpoint / Checkpoint Line pattern.
"""
from odoo import api, fields, models


class GarmentMaintenanceChecklist(models.Model):
    _name = 'garment.maintenance.checklist'
    _description = 'Garment Maintenance Checklist Template'
    _order = 'sequence, name'

    name = fields.Char(string='Checklist Name', required=True)
    sequence = fields.Integer(default=10)
    equipment_type = fields.Selection([
        ('machine', 'Production Machine'),
        ('asset', 'Other Asset'),
        ('both', 'Both'),
    ], string='Applies To', default='both', required=True)
    machine_type = fields.Char(string='Machine Type', help='Free-text match against Machine Type, e.g. Overlock.')
    asset_category = fields.Selection([
        ('utility_generator', 'Generator'),
        ('utility_compressor', 'Compressor'),
        ('utility_transformer', 'Transformer'),
        ('utility_chiller', 'Chiller'),
        ('utility_hvac', 'HVAC System'),
        ('utility_boiler', 'Boiler'),
        ('facility_building', 'Building'),
        ('facility_vehicle', 'Vehicle'),
        ('facility_computer', 'Computer'),
        ('facility_furniture', 'Furniture'),
        ('quality_instrument', 'Quality / Testing Instrument'),
        ('other', 'Other'),
    ], string='Asset Category')
    line_ids = fields.One2many('garment.maintenance.checklist.line', 'checklist_id', string='Checklist Items')
    line_count = fields.Integer(compute='_compute_line_count')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)


class GarmentMaintenanceChecklistLine(models.Model):
    _name = 'garment.maintenance.checklist.line'
    _description = 'Garment Maintenance Checklist Item'
    _order = 'sequence, id'

    checklist_id = fields.Many2one('garment.maintenance.checklist', string='Checklist',
                                    required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    check_item = fields.Char(string='Check Item', required=True)
    is_mandatory = fields.Boolean(string='Mandatory', default=True)
    instructions = fields.Text(string='Instructions')
