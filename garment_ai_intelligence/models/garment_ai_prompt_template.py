# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Reusable, centrally-governed prompt templates so external LLM calls made via
``garment.ai.engine.call_llm()`` are never built from an inline string buried
in a module's Python code. A template uses simple ``{placeholder}`` tokens
(Python ``str.format`` syntax) that callers fill in with real record data.
"""
from odoo import api, fields, models

from .garment_ai_provider_config import AI_FEATURE_SELECTION


class GarmentAIPromptTemplate(models.Model):
    _name = 'garment.ai.prompt.template'
    _description = 'Garment AI Prompt Template'
    _order = 'use_case, sequence, id'

    name = fields.Char(string='Template Name', required=True)
    sequence = fields.Integer(default=10)
    use_case = fields.Selection(AI_FEATURE_SELECTION, string='Use Case', required=True, default='other')
    prompt_text = fields.Text(string='Prompt Text', required=True,
                               help='Use {placeholder} tokens (Python str.format syntax), e.g. '
                                    '"Given buyer {buyer_name} with {order_count} open orders, ..."')
    variable_hint = fields.Char(string='Placeholders',
                                 help='Documentation only, e.g. "{buyer_name}, {order_count}, {style_name}".')
    provider_config_id = fields.Many2one('garment.ai.provider.config', string='Preferred Provider',
                                          help='Optional. If unset, the feature routing on '
                                               'garment.ai.provider.config decides which provider handles '
                                               'calls built from this template.')
    version = fields.Char(string='Version', default='1.0')
    description = fields.Text(string='Description / Governance Notes')
    is_active = fields.Boolean(string='Active', default=True)
    usage_log_ids = fields.One2many('garment.ai.usage.log', 'prompt_template_id', string='Usage Log')
    usage_count = fields.Integer(compute='_compute_usage_count')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('name_use_case_uniq', 'unique(name, use_case, company_id)',
         'A prompt template with this name already exists for this use case.'),
    ]

    @api.depends('usage_log_ids')
    def _compute_usage_count(self):
        for rec in self:
            rec.usage_count = len(rec.usage_log_ids)

    def render(self, **kwargs):
        """Fill the template's {placeholder} tokens from kwargs. Missing
        placeholders fall back to the raw template text rather than raising,
        so a governance/config mistake never blocks the calling business
        flow (same fail-soft philosophy as garment.ai.engine.call_llm)."""
        self.ensure_one()
        try:
            return self.prompt_text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return self.prompt_text

    def action_view_usage_log(self):
        self.ensure_one()
        return {
            'name': 'Usage Log', 'type': 'ir.actions.act_window', 'res_model': 'garment.ai.usage.log',
            'view_mode': 'tree,form', 'domain': [('prompt_template_id', '=', self.id)],
        }
