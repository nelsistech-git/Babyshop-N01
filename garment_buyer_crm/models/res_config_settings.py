# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    garment_ai_provider = fields.Selection([
        ('none', 'Disabled (rule-based scoring only)'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('azure_openai', 'Azure OpenAI'),
        ('custom', 'Custom Endpoint'),
    ], string='AI Provider', config_parameter='garment_ai.provider', default='none')
    garment_ai_api_key = fields.Char(string='AI API Key', config_parameter='garment_ai.api_key')
    garment_ai_api_endpoint = fields.Char(string='AI API Endpoint', config_parameter='garment_ai.api_endpoint',
                                           help='Required for Azure OpenAI / Custom providers.')
    garment_ai_model = fields.Char(string='AI Model Name', config_parameter='garment_ai.model')
