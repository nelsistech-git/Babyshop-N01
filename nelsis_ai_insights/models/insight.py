import json
import logging

import requests

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'claude-sonnet-5-5'


class NelsisAiInsight(models.Model):
    _name = 'nelsis.ai.insight'
    _description = 'AI Insight / Risk Finding'
    _inherit = ['mail.thread']
    _order = 'severity desc, id desc'

    name = fields.Char(required=True)
    kind = fields.Selection([
        ('fake_gps', 'Fake / mock GPS'), ('clock', 'Phone clock manipulation'), ('jump', 'Impossible movement'),
        ('geo_mismatch', 'Claim not supported by map'), ('dup_bill', 'Duplicate bill'),
        ('abnormal_amount', 'Abnormal claim amount'), ('outside_site', 'Punch outside work site'),
        ('late_pattern', 'Repeated late arrival'), ('offline_pattern', 'Frequent offline gaps'),
        ('digest', 'Daily digest'),
    ], required=True, index=True)
    severity = fields.Selection([('0', 'Info'), ('1', 'Low'), ('2', 'Medium'), ('3', 'High')], default='1', required=True)
    score = fields.Integer(string='Risk Score', help='0-100')
    state = fields.Selection([('open', 'Open'), ('reviewed', 'Reviewed'), ('dismissed', 'Dismissed')], default='open',
                             tracking=True, index=True)
    employee_id = fields.Many2one('hr.employee', index=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    date = fields.Date(default=fields.Date.context_today)
    description = fields.Text()
    ai_explanation = fields.Text(string='AI Explanation', readonly=True)
    res_model = fields.Char()
    res_id = fields.Integer()
    fingerprint = fields.Char(index=True, copy=False)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [('fp_uniq', 'unique(fingerprint)', 'Insight already recorded.')]

    def action_review(self):
        self.write({'state': 'reviewed'})

    def action_dismiss(self):
        self.write({'state': 'dismissed'})

    def action_reopen(self):
        self.write({'state': 'open'})

    def action_open_source(self):
        self.ensure_one()
        if self.res_model and self.res_id:
            return {'type': 'ir.actions.act_window', 'res_model': self.res_model, 'res_id': self.res_id,
                    'views': [[False, 'form']]}
        if self.employee_id:
            return self.employee_id.action_open_live_map()

    def action_explain(self):
        """Ask Claude to explain the finding and suggest next steps (needs an API key in Settings)."""
        for rec in self:
            rec.ai_explanation = rec._llm(
                'You are a fraud & HR analytics assistant for a field-force company in Bangladesh. '
                'Explain the finding below in 3 short bullet points: why it matters, the most likely innocent '
                'explanation, and what the administrator should check next. Be neutral and factual.',
                '%s\n%s' % (rec.name, rec.description or ''))

    # ---------------------------------------------------------------- LLM
    def _llm_raw(self, system, user):
        """Text from the model, or None when AI is off / unavailable (never raises)."""
        icp = self.env['ir.config_parameter'].sudo()
        key = icp.get_param('nelsis.ai_api_key')
        if not key:
            return None
        model = icp.get_param('nelsis.ai_model') or DEFAULT_MODEL
        try:
            r = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'},
                data=json.dumps({'model': model, 'max_tokens': 500, 'system': system,
                                 'messages': [{'role': 'user', 'content': user[:6000]}]}),
                timeout=25)
            r.raise_for_status()
            return ''.join(b.get('text', '') for b in r.json().get('content', [])).strip() or None
        except Exception as e:  # noqa: BLE001
            _logger.warning('AI call failed: %s', e)
            return None

    def _llm(self, system, user):
        """Same as _llm_raw but returns a readable message instead of None (used by the Explain button)."""
        if not self.env['ir.config_parameter'].sudo().get_param('nelsis.ai_api_key'):
            return _('AI explanation is off. Add an API key in Settings > Field Force > AI.')
        return self._llm_raw(system, user) or _('AI service unavailable right now.')

    @api.model
    def _cron_scan(self):
        self.env['nelsis.ai.engine'].scan()

    @api.model
    def _cron_digest(self):
        self.env['nelsis.ai.engine'].daily_digest()
