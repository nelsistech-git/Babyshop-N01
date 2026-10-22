# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentCuttingQc(models.Model):
    """Cutting Quality Integration — Panel Measurement, Notch Accuracy,
    Cutting Defect, Shade Matching, Quantity Accuracy. See Production
    Management SRS s.27."""
    _name = 'garment.cutting.qc'
    _description = 'Garment Cutting QC Inspection'
    _order = 'inspection_date desc'

    cutting_order_id = fields.Many2one('garment.cutting.order', string='Cutting Order',
                                       required=True, ondelete='cascade')
    bundle_id = fields.Many2one('garment.cutting.bundle', string='Bundle')
    inspector_id = fields.Many2one('garment.hr.employee', string='Inspector')
    inspection_date = fields.Date(string='Inspection Date', default=fields.Date.context_today)

    panel_measurement_ok = fields.Boolean(string='Panel Measurement OK', default=True)
    notch_accuracy_ok = fields.Boolean(string='Notch Accuracy OK', default=True)
    shade_matching_ok = fields.Boolean(string='Shade Matching OK', default=True)
    quantity_accuracy_ok = fields.Boolean(string='Quantity Accuracy OK', default=True)
    defect_qty = fields.Float(string='Defect Quantity (PCS)')
    checked_qty = fields.Float(string='Checked Quantity (PCS)')

    result = fields.Selection([
        ('pass', 'Approved'), ('fail', 'Rejected'),
    ], string='Result', default='pass')
    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
