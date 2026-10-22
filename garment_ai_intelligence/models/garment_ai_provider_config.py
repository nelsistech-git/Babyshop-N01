# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
AI Provider Configuration — the "proper home" config layer referenced in the
module description. Several sibling modules (garment_buyer_crm,
garment_order_management, garment_quality, garment_maintenance,
garment_compliance, garment_plm...) extend the shared abstract
``garment.ai.engine`` (defined in garment_buyer_crm) with their own
deterministic heuristic scorers, and garment_buyer_crm's base engine reads
provider credentials from plain ``ir.config_parameter`` keys
(``garment_ai.provider`` / ``.api_key`` / ...). This model replaces that with
a real, editable, auditable record: one or more named provider
configurations, each enabled/disabled independently, with per-feature
routing so (for example) "demand_forecast" calls can be routed to a cheaper
model than "quality_prediction".

This module's own ``garment.ai.engine.call_llm()`` (see
``garment_ai_engine.py``) is the only in-suite caller of these records today;
see IMPLEMENTATION_NOTES.md for the plan to let sibling modules opt into it.
"""
from odoo import api, fields, models

# Shared "what is this AI call for" vocabulary, reused across the provider
# routing lines, the prompt template library and the usage log so all three
# stay in lock-step.
AI_FEATURE_SELECTION = [
    ('demand_forecast', 'Demand Forecasting'),
    ('quality_prediction', 'Quality Risk Prediction'),
    ('cost_optimization', 'Cost Optimization'),
    ('procurement_intelligence', 'Procurement Intelligence'),
    ('hr_analytics', 'HR Analytics'),
    ('finance_intelligence', 'Finance Intelligence'),
    ('risk_alert', 'Risk / Delay Alert'),
    ('anomaly_detection', 'Anomaly Detection'),
    ('similarity_match', 'Similarity Matching'),
    ('recommendation', 'Recommendation Engine'),
    ('report_generation', 'Report Generation'),
    ('chatbot', 'AI Assistant / Chatbot'),
    ('email_drafting', 'Email / Communication Drafting'),
    ('other', 'Other'),
]

_PROVIDER_DEFAULT_ENDPOINT = {
    'openai': 'https://api.openai.com/v1/chat/completions',
    'anthropic': 'https://api.anthropic.com/v1/messages',
}
_PROVIDER_DEFAULT_MODEL = {
    'openai': 'gpt-4o-mini',
    'anthropic': 'claude-3-5-haiku-20241022',
}


class GarmentAIProviderConfig(models.Model):
    _name = 'garment.ai.provider.config'
    _description = 'Garment AI Provider Configuration'
    _inherit = ['mail.thread']
    _order = 'sequence, id'

    name = fields.Char(string='Configuration Name', required=True, tracking=True,
                        help='e.g. "OpenAI - Production" / "Azure - Cost Sensitive Features".')
    sequence = fields.Integer(default=10)
    provider = fields.Selection([
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('azure_openai', 'Azure OpenAI'),
        ('custom', 'Custom Endpoint'),
    ], string='Provider', required=True, default='openai', tracking=True)

    api_key = fields.Char(string='API Key', groups='garment_ai_intelligence.group_ai_admin',
                           help='Stored as plain text on this Community-edition sandbox model — in a '
                                'production deployment this should move to an encrypted secret store. '
                                'Visible to the AI Administrator group only.')
    api_endpoint = fields.Char(string='API Endpoint', tracking=True,
                                help='Required for Azure OpenAI / Custom. Left blank for OpenAI/Anthropic '
                                     'to use the provider default endpoint.')
    model_name = fields.Char(string='Model Name', tracking=True,
                              help='e.g. gpt-4o-mini, claude-3-5-haiku-20241022, or a custom deployment name.')

    is_enabled = fields.Boolean(string='Enabled', default=True, tracking=True)
    is_default = fields.Boolean(string='Default Provider', default=False, tracking=True,
                                 help='Used as fallback when a feature has no explicit routing line below.')

    route_ids = fields.One2many('garment.ai.provider.feature.line', 'config_id', string='Feature Routing')
    route_count = fields.Integer(compute='_compute_route_count')

    usage_log_ids = fields.One2many('garment.ai.usage.log', 'provider_config_id', string='Usage Log')
    usage_count = fields.Integer(compute='_compute_usage_count')
    total_estimated_cost = fields.Monetary(compute='_compute_usage_count', currency_field='currency_id',
                                            string='Total Estimated Cost')

    notes = fields.Text(string='Notes')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)',
         'An AI Provider Configuration with this name already exists for this company.'),
    ]

    @api.depends('route_ids')
    def _compute_route_count(self):
        for rec in self:
            rec.route_count = len(rec.route_ids)

    @api.depends('usage_log_ids.estimated_cost')
    def _compute_usage_count(self):
        for rec in self:
            rec.usage_count = len(rec.usage_log_ids)
            rec.total_estimated_cost = sum(rec.usage_log_ids.mapped('estimated_cost'))

    @api.onchange('provider')
    def _onchange_provider(self):
        for rec in self:
            if rec.provider in _PROVIDER_DEFAULT_MODEL and not rec.model_name:
                rec.model_name = _PROVIDER_DEFAULT_MODEL[rec.provider]

    def effective_endpoint(self):
        self.ensure_one()
        return self.api_endpoint or _PROVIDER_DEFAULT_ENDPOINT.get(self.provider)

    def effective_model(self):
        self.ensure_one()
        return self.model_name or _PROVIDER_DEFAULT_MODEL.get(self.provider, 'gpt-4o-mini')

    def estimate_cost(self, tokens_input, tokens_output):
        """Very rough, deterministic per-1K-token cost estimate for cost-governance
        purposes only — NOT a real provider billing integration. Uses a flat
        placeholder rate; a real deployment would look this up per model."""
        self.ensure_one()
        rate_in, rate_out = 0.00015, 0.0006  # USD / 1K tokens, GPT-4o-mini-class placeholder
        return round((tokens_input or 0) / 1000.0 * rate_in + (tokens_output or 0) / 1000.0 * rate_out, 6)

    @api.model
    def get_config_for_feature(self, feature_code):
        """Return the best enabled ``garment.ai.provider.config`` for a given
        feature code: an explicit routing line first, then the default
        provider, else an empty recordset."""
        route = self.env['garment.ai.provider.feature.line'].search([
            ('feature', '=', feature_code), ('config_id.is_enabled', '=', True),
        ], order='sequence', limit=1)
        if route:
            return route.config_id
        return self.search([('is_default', '=', True), ('is_enabled', '=', True)], limit=1)

    def action_view_usage_log(self):
        self.ensure_one()
        return {
            'name': 'Usage Log', 'type': 'ir.actions.act_window', 'res_model': 'garment.ai.usage.log',
            'view_mode': 'tree,form', 'domain': [('provider_config_id', '=', self.id)],
        }


class GarmentAIProviderFeatureLine(models.Model):
    _name = 'garment.ai.provider.feature.line'
    _description = 'Garment AI Provider Feature Routing Line'
    _order = 'sequence, id'

    config_id = fields.Many2one('garment.ai.provider.config', string='Provider Configuration',
                                 required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    feature = fields.Selection(AI_FEATURE_SELECTION, string='Feature', required=True)

    _sql_constraints = [
        ('config_feature_uniq', 'unique(config_id, feature)',
         'This feature is already routed on this provider configuration.'),
    ]
