# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
AI Industrial Engineering System (SRS s.35-38, s.51) — AI Line Balancing
Recommendation, AI SMV Prediction, AI Capacity Forecast and AI Productivity
Coach. A full ML pipeline is out of scope for an Odoo Community addon; this
model provides the data structure and a manual/API entry point (see
``GET /api/ie/...`` in SRS s.51 and IMPLEMENTATION_NOTES.md) so an external
AI service can log structured recommendations the IE team can act on —
matching the pattern used by ``garment.quality.ai.analysis`` (garment_quality)
and ``garment.ai.engine`` (garment_buyer_crm).
"""
from odoo import api, fields, models, _


class GarmentIeAiInsight(models.Model):
    _name = 'garment.ie.ai.insight'
    _description = 'Garment IE AI Insight'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'analysis_date desc'

    name = fields.Char(string='Reference', copy=False, readonly=True, default=lambda s: _('New'))
    insight_type = fields.Selection([
        ('line_balancing', 'AI Line Balancing Recommendation'),
        ('smv_prediction', 'AI SMV Prediction'),
        ('capacity_forecast', 'AI Capacity Forecast'),
        ('productivity_coach', 'AI Productivity Coach'),
    ], string='Insight Type', required=True, tracking=True)

    style_id = fields.Many2one('garment.style', string='Style')
    line_id = fields.Many2one('garment.production.line', string='Production Line')
    operation_id = fields.Many2one('garment.ie.operation', string='Operation')
    employee_id = fields.Many2one('garment.hr.employee', string='Employee')

    current_value = fields.Char(string='Current Value', help='e.g. "72% Efficiency", "Low Output"')
    input_summary = fields.Text(string='Analyzed Data Summary')
    recommendation = fields.Text(string='Recommendation', required=True)
    expected_value = fields.Char(string='Expected Value', help='e.g. "82% Efficiency", "+15% Output"')
    confidence_pct = fields.Float(string='Confidence (%)')

    status = fields.Selection([
        ('new', 'New'), ('reviewed', 'Reviewed'), ('applied', 'Applied'), ('dismissed', 'Dismissed'),
    ], string='Status', default='new', tracking=True)
    analysis_date = fields.Datetime(string='Analysis Date', default=fields.Datetime.now)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.ie.ai.insight') or _('New')
        return super().create(vals_list)

    def action_mark_reviewed(self):
        self.write({'status': 'reviewed'})

    def action_apply(self):
        self.write({'status': 'applied'})

    def action_dismiss(self):
        self.write({'status': 'dismissed'})
