# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmResponseTime(models.Model):
    _name = 'crm.response.time'
    _description = 'Agent Response Time Log'
    _order = 'response_date desc'

    session_id = fields.Many2one('crm.chat.session', string='Conversation',
                                  required=True, ondelete='cascade', index=True)
    agent_id = fields.Many2one('res.users', string='Agent', index=True)
    channel_id = fields.Many2one('crm.channel', string='Channel', index=True)
    waiting_since = fields.Datetime(string='Customer Message At', required=True)
    response_date = fields.Datetime(string='Agent Response At', required=True)
    response_seconds = fields.Integer(string='Response Time (s)', compute='_compute_response_seconds', store=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('waiting_since', 'response_date')
    def _compute_response_seconds(self):
        for rec in self:
            if rec.waiting_since and rec.response_date:
                rec.response_seconds = int((rec.response_date - rec.waiting_since).total_seconds())
            else:
                rec.response_seconds = 0
