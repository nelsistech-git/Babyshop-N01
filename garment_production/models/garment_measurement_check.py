# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentMeasurementCheck(models.Model):
    """Final Measurement Checking (Chest, Length, Sleeve, Waist, Inseam...).
    See Production Management SRS s.48."""
    _name = 'garment.measurement.check'
    _description = 'Garment Finishing Measurement Check'
    _order = 'check_date desc'

    finishing_order_id = fields.Many2one('garment.finishing.order', string='Finishing Order',
                                         required=True, ondelete='cascade')
    style_id = fields.Many2one('garment.style', related='finishing_order_id.style_id', string='Style', store=True)
    measurement_point = fields.Selection([
        ('chest', 'Chest'), ('length', 'Length'), ('sleeve', 'Sleeve'),
        ('waist', 'Waist'), ('inseam', 'Inseam'), ('other', 'Other'),
    ], string='Measurement Point', required=True)
    required_value = fields.Float(string='Required Value (Inch)')
    actual_value = fields.Float(string='Actual Value (Inch)')
    tolerance = fields.Float(string='Tolerance (Inch)', default=0.25)
    result = fields.Selection([
        ('pass', 'Pass'), ('fail', 'Fail'),
    ], string='Result', compute='_compute_result', store=True)
    checked_by_id = fields.Many2one('garment.hr.employee', string='Checked By')
    check_date = fields.Date(string='Check Date', default=fields.Date.context_today)

    @api.depends('required_value', 'actual_value', 'tolerance')
    def _compute_result(self):
        for rec in self:
            if not rec.required_value:
                rec.result = 'pass'
                continue
            rec.result = 'pass' if abs(rec.actual_value - rec.required_value) <= rec.tolerance else 'fail'
