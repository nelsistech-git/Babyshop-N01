# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
AI Predictive Maintenance (Maintenance & Asset Mgmt SRS sec. 37-40,
CMMS SRS sec. 35, 39). A full ML pipeline is out of scope for an Odoo
Community addon; this model provides the structured log entry point
(breakdown risk, recommended schedule, spare-parts demand forecast) and
a deterministic heuristic scorer so the feature works end-to-end
without an external AI provider configured — same pattern as
``garment.quality.ai.analysis`` (garment_quality).
"""
from odoo import api, fields, models, _


class GarmentMaintenanceAiPrediction(models.Model):
    _name = 'garment.maintenance.ai.prediction'
    _description = 'Garment Maintenance AI Predictive Insight'
    _inherit = ['mail.thread']
    _order = 'analysis_date desc'

    name = fields.Char(string='Reference', copy=False, readonly=True, default=lambda s: _('New'))
    prediction_type = fields.Selection([
        ('breakdown_risk', 'Breakdown Risk Prediction'),
        ('schedule_recommendation', 'Maintenance Schedule Recommendation'),
        ('spare_forecast', 'Spare Parts Demand Forecast'),
    ], string='Prediction Type', required=True, default='breakdown_risk')

    equipment_type = fields.Selection([
        ('machine', 'Production Machine'),
        ('asset', 'Other Asset'),
    ], string='Equipment Type', default='machine')
    machine_id = fields.Many2one('garment.production.machine', string='Machine')
    asset_id = fields.Many2one('garment.asset', string='Asset')
    material_id = fields.Many2one('garment.material', string='Spare Part',
                                   domain=[('category', '=', 'spare_parts')],
                                   help='Used for Spare Parts Demand Forecast predictions.')

    risk_level = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], string='Risk Level')
    predicted_issue = fields.Char(string='Predicted Issue')
    probability_pct = fields.Float(string='Probability (%)')
    predicted_demand_qty = fields.Float(string='Predicted Demand Quantity')
    recommendation = fields.Text(string='Recommended Action')
    recommended_date = fields.Date(string='Recommended Maintenance Date')

    analysis_date = fields.Datetime(string='Analysis Date', default=fields.Datetime.now)
    status = fields.Selection([
        ('new', 'New'), ('reviewed', 'Reviewed'), ('action_taken', 'Action Taken'), ('dismissed', 'Dismissed'),
    ], string='Status', default='new', tracking=True)
    workorder_id = fields.Many2one('garment.maintenance.workorder', string='Resulting Work Order')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.maintenance.ai.prediction') or _('New')
        return super().create(vals_list)

    @api.model
    def run_breakdown_risk_prediction(self, machine):
        """Deterministic heuristic proxy for AI breakdown-risk scoring,
        based on recent breakdown frequency and downtime ratio."""
        Workorder = self.env['garment.maintenance.workorder']
        recent = Workorder.search([
            ('machine_id', '=', machine.id), ('wo_type', '=', 'breakdown'),
            ('state', 'in', ('completed', 'closed')),
        ], limit=20)
        breakdown_count = len(recent)
        downtime_hours = sum(recent.mapped('downtime_hours'))

        if breakdown_count >= 5 or downtime_hours >= 40 or machine.status == 'breakdown':
            risk, probability = 'high', 85.0
            issue = 'Recurring failure pattern detected — component wear likely.'
            recommendation = 'Schedule inspection within 7 days and stock the frequently replaced spare part.'
        elif breakdown_count >= 2 or downtime_hours >= 15:
            risk, probability = 'medium', 55.0
            issue = 'Above-average breakdown frequency.'
            recommendation = 'Schedule a preventive check within 30 days.'
        else:
            risk, probability = 'low', 15.0
            issue = 'No significant failure pattern detected.'
            recommendation = 'Continue normal preventive maintenance schedule.'

        return self.create({
            'prediction_type': 'breakdown_risk',
            'equipment_type': 'machine',
            'machine_id': machine.id,
            'risk_level': risk,
            'predicted_issue': issue,
            'probability_pct': probability,
            'recommendation': recommendation,
        })

    @api.model
    def run_spare_forecast(self, material):
        """Deterministic heuristic proxy for spare-parts demand forecasting
        based on the last 90 days of issue moves for the material."""
        moves = self.env['garment.stock.move'].search([
            ('material_id', '=', material.id), ('move_type', '=', 'issue'), ('state', '=', 'done'),
        ], limit=90)
        monthly_usage = sum(moves.mapped('quantity')) / 3.0 if moves else 0.0
        predicted = monthly_usage * 1.15
        recommendation = _('Increase stock ahead of forecasted demand.') if predicted > material.on_hand_qty \
            else _('Current stock is sufficient for forecasted demand.')
        return self.create({
            'prediction_type': 'spare_forecast',
            'material_id': material.id,
            'predicted_demand_qty': predicted,
            'recommendation': recommendation,
        })
