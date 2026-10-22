# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
API call audit log for cost governance (SRS sections 20, 50-53, 57: AI
Security / Model Monitoring / AI Dashboard cost & prediction counters).
Every call made through ``garment.ai.engine.call_llm()`` writes exactly one
row here, success or failure, so token spend and latency are always
traceable back to the feature, provider and (optionally) source record that
triggered it.
"""
from odoo import api, fields, models, _

from .garment_ai_provider_config import AI_FEATURE_SELECTION


class GarmentAIUsageLog(models.Model):
    _name = 'garment.ai.usage.log'
    _description = 'Garment AI API Usage Log'
    _order = 'request_date desc, id desc'

    name = fields.Char(string='Reference', copy=False, readonly=True, default=lambda s: _('New'))
    provider_config_id = fields.Many2one('garment.ai.provider.config', string='Provider Configuration',
                                          ondelete='set null')
    prompt_template_id = fields.Many2one('garment.ai.prompt.template', string='Prompt Template',
                                          ondelete='set null')
    feature = fields.Selection(AI_FEATURE_SELECTION, string='Feature')

    res_model = fields.Char(string='Related Model', help='Technical name of the record this AI call was made for.')
    res_id = fields.Integer(string='Related Record ID')
    res_name = fields.Char(string='Related Record', compute='_compute_res_name')

    user_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user)
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, required=True)

    status = fields.Selection([
        ('success', 'Success'), ('error', 'Error'),
    ], string='Status', default='success', required=True)
    error_message = fields.Text(string='Error Message')

    tokens_input = fields.Integer(string='Tokens (Input)')
    tokens_output = fields.Integer(string='Tokens (Output)')
    tokens_total = fields.Integer(string='Tokens (Total)', compute='_compute_tokens_total', store=True)
    estimated_cost = fields.Monetary(string='Estimated Cost', currency_field='currency_id')
    latency_ms = fields.Float(string='Latency (ms)')

    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('tokens_input', 'tokens_output')
    def _compute_tokens_total(self):
        for rec in self:
            rec.tokens_total = (rec.tokens_input or 0) + (rec.tokens_output or 0)

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
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.ai.usage.log') or _('New')
        return super().create(vals_list)

    def action_view_source(self):
        self.ensure_one()
        if not (self.res_model and self.res_id):
            return False
        return {
            'type': 'ir.actions.act_window', 'res_model': self.res_model, 'res_id': self.res_id,
            'view_mode': 'form', 'target': 'current',
        }
