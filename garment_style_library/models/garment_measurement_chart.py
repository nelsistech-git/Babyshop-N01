# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentMeasurementChart(models.Model):
    """Measurement Chart header (SRS section 17) — garment.measurement.chart."""
    _name = 'garment.measurement.chart'
    _description = 'Garment Measurement Chart'
    _inherit = ['mail.thread']
    _order = 'chart_number desc'

    chart_number = fields.Char(string='Chart Number', copy=False, readonly=True, default=lambda s: _('New'))
    style_id = fields.Many2one('garment.style', string='Style', required=True, ondelete='cascade')
    version = fields.Char(string='Version', default='1.0')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', related='style_id.buyer_id', store=True)
    product_type = fields.Char(string='Product Type')
    unit = fields.Selection([('cm', 'CM'), ('inch', 'Inch')], string='Unit', default='cm')
    revision = fields.Integer(string='Revision', default=0)
    status = fields.Selection([
        ('draft', 'Draft'), ('under_review', 'Under Review'), ('approved', 'Approved'),
    ], string='Status', default='draft')
    grade_rule_id = fields.Many2one('garment.grade.rule', string='Applied Grade Rule',
                                     help='Grade rule used to compute/verify the graded sizes on this chart '
                                          '(SRS section 18 Grade Calculation).')
    line_ids = fields.One2many('garment.measurement.line', 'chart_id', string='Measurement Points')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('chart_number', _('New')) == _('New'):
                vals['chart_number'] = self.env['ir.sequence'].next_by_code('garment.measurement.chart') or _('New')
        return super().create(vals_list)


class GarmentMeasurementLine(models.Model):
    """Measurement points (SRS section 17) — garment.measurement.line."""
    _name = 'garment.measurement.line'
    _description = 'Garment Measurement Point'
    _order = 'sequence'

    chart_id = fields.Many2one('garment.measurement.chart', string='Measurement Chart', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    measurement_point_id = fields.Many2one('garment.measurement.point', string='Measurement Point (Master)',
                                             help='Optional link to the standard Measurement Point master; '
                                                  'selecting one fills in the Point Code/Description/Method below.')
    point_code = fields.Char(string='Point Code', required=True)
    description = fields.Char(string='Description', required=True,
                               help='e.g. Chest Width, Waist Width, Shoulder Width, Sleeve Length...')
    base_size_value = fields.Float(string='Base Size Value')
    grade_rule_value = fields.Float(string='Grade Rule (+/- per size)')
    tolerance_plus = fields.Float(string='Tolerance (+)')
    tolerance_minus = fields.Float(string='Tolerance (-)')
    measurement_method = fields.Char(string='Measurement Method',
                                      help='How this point is physically measured.')
    illustration_reference = fields.Binary(string='Illustration Reference', attachment=True)

    @api.onchange('measurement_point_id')
    def _onchange_measurement_point_id(self):
        for rec in self:
            if rec.measurement_point_id:
                rec.point_code = rec.measurement_point_id.point_code
                rec.description = rec.measurement_point_id.name
                rec.measurement_method = rec.measurement_point_id.default_measurement_method
                rec.illustration_reference = rec.measurement_point_id.illustration_reference
