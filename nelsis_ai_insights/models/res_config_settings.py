from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nelsis_ai_api_key = fields.Char(string='AI API Key (Anthropic)', config_parameter='nelsis.ai_api_key')
    nelsis_ai_model = fields.Char(string='AI Model', config_parameter='nelsis.ai_model', default='claude-sonnet-5-5')
