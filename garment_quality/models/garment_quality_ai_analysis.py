# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentQualityAiAnalysis(models.Model):
    """AI Quality Insight log — records the output of AI quality risk
    prediction, defect trend analysis, supplier scoring, computer-vision
    defect detection and IoT machine-quality monitoring. A full ML / vision
    / IoT pipeline is out of scope for an Odoo Community addon; this model
    provides the data structure and manual/API entry point so those systems
    (or a future integration) can log structured insights the quality team
    can act on. See AI Quality Prediction System (base QMS SRS sec. 41-46),
    AI Quality Prediction System / Computer Vision / IoT (Garment QMS SRS
    sec. 39-42) and AI Vision Quality Detection / AI Quality Prediction
    (Advanced QMS SRS sec. 40-41, model 'garment.ai.quality.analysis')."""
    _name = 'garment.quality.ai.analysis'
    _description = 'Garment Quality AI Insight'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', copy=False, readonly=True, default=lambda s: _('New'))
    analysis_type = fields.Selection([
        ('risk_prediction', 'Quality Risk Prediction'),
        ('defect_trend', 'Defect Trend Analysis'),
        ('supplier_score', 'AI Supplier Quality Score'),
        ('root_cause', 'AI Root Cause Detection'),
        ('computer_vision', 'Computer Vision Detection'),
        ('iot_monitoring', 'IoT Machine Quality Monitoring'),
        ('inspection_planning', 'Automated Inspection Planning'),
    ], string='Analysis Type', required=True)
    style_id = fields.Many2one('garment.style', string='Style')
    supplier_id = fields.Many2one('garment.supplier', string='Supplier')
    sewing_line = fields.Char(string='Sewing Line')
    production_order_id = fields.Char(string='Production Order Ref.',
                                       help='Soft reference — see IMPLEMENTATION_NOTES.md.')
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Risk Level')
    predicted_issue = fields.Char(string='Predicted / Detected Issue')
    probability = fields.Float(string='Probability (%)')
    confidence = fields.Float(string='Confidence (%)', help='Used for computer-vision detections')
    recommendation = fields.Text(string='Recommendation')
    source_data_summary = fields.Text(string='Analyzed Data Summary')
    analysis_date = fields.Datetime(string='Analysis Date', default=fields.Datetime.now)
    status = fields.Selection([
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('action_taken', 'Action Taken'),
        ('dismissed', 'Dismissed'),
    ], string='Status', default='new', tracking=True)
    linked_inspection_id = fields.Many2one('garment.quality.inspection', string='Linked Inspection')
    linked_capa_id = fields.Many2one('garment.quality.capa', string='Linked CAPA')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.quality.ai.analysis') or _('New')
        return super().create(vals_list)
