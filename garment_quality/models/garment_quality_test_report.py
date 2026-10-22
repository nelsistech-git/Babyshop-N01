# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentQualityTestReport(models.Model):
    """Lab / physical Test Report — fabric physical tests, washing tests
    (shrinkage, color fastness) and accessory tests (pull strength). See
    Fabric Quality Inspection (base QMS SRS sec. 10), Washing Test
    Management (base QMS SRS sec. 29) and Accessories Quality Control
    (Advanced QMS SRS sec. 14)."""
    _name = 'garment.quality.test.report'
    _description = 'Garment Quality Test Report'
    _inherit = ['mail.thread']
    _order = 'test_date desc'

    report_no = fields.Char(string='Report No.', copy=False, readonly=True, default=lambda s: _('New'))
    test_type = fields.Selection([
        ('shrinkage', 'Shrinkage Test'),
        ('color_fastness_wash', 'Color Fastness - Washing'),
        ('color_fastness_rub', 'Color Fastness - Rubbing'),
        ('gsm', 'GSM / Weight Test'),
        ('width', 'Fabric Width Test'),
        ('pull_strength', 'Pull Strength (Button / Zipper)'),
        ('chemical', 'Chemical / Compliance Test'),
        ('hand_feel', 'Hand Feel Test'),
        ('other', 'Other'),
    ], string='Test Type', required=True)
    inspection_id = fields.Many2one('garment.quality.inspection', string='Related Inspection')
    material_id = fields.Many2one('garment.material', string='Material')
    style_id = fields.Many2one('garment.style', string='Style')
    supplier_id = fields.Many2one('garment.supplier', string='Supplier')
    test_date = fields.Date(string='Test Date', default=fields.Date.context_today)
    tested_by_id = fields.Many2one('res.users', string='Tested By', default=lambda s: s.env.user)
    spec_value = fields.Char(string='Spec / Target', help='e.g. "<= 3%"')
    actual_value = fields.Char(string='Actual Result', help='e.g. "2%"')
    tolerance = fields.Char(string='Tolerance')
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Result', default='pass', tracking=True)
    report_file = fields.Binary(string='Report File', attachment=True)
    report_filename = fields.Char(string='Report Filename')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('report_no', _('New')) == _('New'):
                vals['report_no'] = self.env['ir.sequence'].next_by_code('garment.quality.test.report') or _('New')
        return super().create(vals_list)
