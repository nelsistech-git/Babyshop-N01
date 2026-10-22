# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentProductionConsumption(models.Model):
    """Planned vs Actual Material Consumption & variance, linked to the BOM
    line. See Production Management SRS s.15, Shop Floor SRS s.32
    (Production Material Consumption Tracking) and s.33 (Wastage)."""
    _name = 'garment.production.consumption'
    _description = 'Garment Production Material Consumption'
    _order = 'production_order_id'

    production_order_id = fields.Many2one('garment.production.order', string='Production Order',
                                           required=True, ondelete='cascade')
    bom_line_id = fields.Many2one('garment.bom.line', string='BOM Line')
    material_id = fields.Many2one('garment.material', string='Material', required=True)
    department = fields.Selection([
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('washing', 'Washing'),
        ('finishing', 'Finishing'), ('packing', 'Packing'),
    ], string='Department', default='cutting')

    uom = fields.Char(string='UoM')
    planned_qty = fields.Float(string='Planned Consumption')
    actual_qty = fields.Float(string='Actual Consumption')
    variance_qty = fields.Float(string='Variance', compute='_compute_variance', store=True)
    variance_pct = fields.Float(string='Variance (%)', compute='_compute_variance', store=True)
    wastage_qty = fields.Float(string='Wastage Quantity')
    wastage_pct = fields.Float(string='Wastage (%)', compute='_compute_variance', store=True)
    wastage_reason = fields.Char(string='Wastage Reason')
    wastage_approved = fields.Boolean(string='Wastage Approved')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('planned_qty', 'actual_qty', 'wastage_qty')
    def _compute_variance(self):
        for rec in self:
            rec.variance_qty = rec.actual_qty - rec.planned_qty
            rec.variance_pct = (rec.variance_qty / rec.planned_qty * 100.0) if rec.planned_qty else 0.0
            rec.wastage_pct = (rec.wastage_qty / rec.planned_qty * 100.0) if rec.planned_qty else 0.0
