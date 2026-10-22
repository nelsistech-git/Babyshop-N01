# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentMaterialConsumption(models.Model):
    """Size-wise and Color-wise Consumption (SRS section 14-15), plus
    Material Consumption Monitoring — planned vs actual, wastage and
    efficiency (SRS section 41) — garment.material.consumption."""
    _name = 'garment.material.consumption'
    _description = 'Garment Material Consumption Breakdown'
    _order = 'sequence'

    bom_id = fields.Many2one('garment.bom', string='BOM', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    breakdown_type = fields.Selection([
        ('size', 'Size-wise'), ('color', 'Color-wise'),
    ], string='Breakdown Type', required=True)
    fabric_bom_id = fields.Many2one('garment.fabric.bom', string='Fabric Line',
                                     domain="[('bom_id', '=', bom_id)]")
    trim_bom_id = fields.Many2one('garment.trim.bom', string='Trim Line',
                                   domain="[('bom_id', '=', bom_id)]")
    packaging_bom_id = fields.Many2one('garment.packaging.bom', string='Packaging Line',
                                        domain="[('bom_id', '=', bom_id)]")
    artwork_reference = fields.Char(string='Artwork Reference')
    size_code = fields.Char(string='Size')
    color_name = fields.Char(string='Color')
    size_ratio = fields.Float(string='Size Ratio (%)')
    consumption_value = fields.Float(string='Consumption Value (Planned)')
    quantity = fields.Integer(string='Quantity')
    total_requirement = fields.Float(string='Total Requirement', compute='_compute_total_requirement', store=True)

    # Material Consumption Monitoring (SRS section 41)
    issued_qty = fields.Float(string='Issued Quantity')
    actual_consumption = fields.Float(string='Actual Consumption')
    returned_qty = fields.Float(string='Returned Quantity')
    wastage_qty = fields.Float(string='Wastage')
    consumption_efficiency_pct = fields.Float(string='Consumption Efficiency %',
                                               compute='_compute_efficiency', store=True)

    @api.depends('consumption_value', 'quantity')
    def _compute_total_requirement(self):
        for rec in self:
            rec.total_requirement = (rec.consumption_value or 0.0) * (rec.quantity or 0.0)

    @api.depends('consumption_value', 'actual_consumption')
    def _compute_efficiency(self):
        for rec in self:
            rec.consumption_efficiency_pct = (
                (rec.consumption_value / rec.actual_consumption) * 100.0
                if rec.actual_consumption else 0.0)
