# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Unified cross-module AI Insight / Prediction log. Every AI-generated
prediction, risk alert, anomaly, recommendation or similarity match anywhere
in the suite can log ONE row here, pointed back at its source record via the
generic ``res_model``/``res_id`` pair — the same "source of truth" role
``garment.order.risk``, ``garment.quality.ai.analysis``,
``garment.maintenance.ai.prediction`` and ``garment.ie.ai.insight`` each play
locally today. See IMPLEMENTATION_NOTES.md for the (not-yet-done) plan to
let those consolidate into this model.

This module writes rows here from exactly one place today:
``GarmentDemandForecast.action_generate_demand_forecast()``.
"""
from odoo import api, fields, models, _


class GarmentAIInsight(models.Model):
    _name = 'garment.ai.insight'
    _description = 'Garment AI Insight / Prediction (Unified Log)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'insight_date desc, id desc'

    name = fields.Char(string='Reference', copy=False, readonly=True, default=lambda s: _('New'))
    insight_type = fields.Selection([
        ('demand_forecast', 'Demand Forecast'),
        ('risk_alert', 'Risk Alert'),
        ('anomaly', 'Anomaly Detection'),
        ('recommendation', 'Recommendation'),
        ('similarity_match', 'Similarity Match'),
    ], string='Insight Type', required=True, default='recommendation', tracking=True)

    res_model = fields.Char(string='Related Model', required=True,
                             help='Technical model name of the source record, e.g. garment.demand.forecast.')
    res_id = fields.Integer(string='Related Record ID', required=True)
    res_name = fields.Char(string='Related Record', compute='_compute_res_name', store=True)

    confidence = fields.Float(string='Confidence (%)', help='0-100. Confidence of the underlying prediction.')
    explanation = fields.Text(string='Explanation', help='Free-text rationale — what data/heuristic produced '
                                                           'this insight and why.')
    recommendation = fields.Text(string='Recommended Action')

    source = fields.Selection([
        ('heuristic', 'Deterministic Heuristic'),
        ('ai_provider', 'External AI Provider'),
    ], string='Source', default='heuristic', required=True,
        help='Whether this insight came from an in-suite deterministic calculation or an external LLM/AI call.')
    provider_config_id = fields.Many2one('garment.ai.provider.config', string='AI Provider Used')
    usage_log_id = fields.Many2one('garment.ai.usage.log', string='API Usage Log', ondelete='set null')

    insight_date = fields.Datetime(string='Generated On', default=fields.Datetime.now, required=True)
    status = fields.Selection([
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('actioned', 'Actioned'),
        ('dismissed', 'Dismissed'),
    ], string='Status', default='new', required=True, tracking=True)
    reviewed_by_id = fields.Many2one('res.users', string='Reviewed By', readonly=True, copy=False)
    reviewed_date = fields.Datetime(string='Reviewed On', readonly=True, copy=False)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for rec in self:
            rec.res_name = False
            if rec.res_model and rec.res_id and rec.res_model in self.env:
                record = self.env[rec.res_model].browse(rec.res_id).exists()
                if record:
                    rec.res_name = record.display_name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.ai.insight') or _('New')
        return super().create(vals_list)

    def action_view_source(self):
        self.ensure_one()
        if not (self.res_model and self.res_id and self.res_model in self.env):
            return False
        return {
            'type': 'ir.actions.act_window', 'res_model': self.res_model, 'res_id': self.res_id,
            'view_mode': 'form', 'target': 'current',
        }

    def action_mark_reviewed(self):
        self.write({'status': 'reviewed', 'reviewed_by_id': self.env.user.id, 'reviewed_date': fields.Datetime.now()})

    def action_mark_actioned(self):
        self.write({'status': 'actioned', 'reviewed_by_id': self.env.user.id, 'reviewed_date': fields.Datetime.now()})

    def action_dismiss(self):
        self.write({'status': 'dismissed', 'reviewed_by_id': self.env.user.id, 'reviewed_date': fields.Datetime.now()})

    def action_reset_new(self):
        self.write({'status': 'new', 'reviewed_by_id': False, 'reviewed_date': False})
