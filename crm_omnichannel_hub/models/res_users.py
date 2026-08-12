# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    omni_assigned_session_count = fields.Integer(
        string='Assigned Conversations', compute='_compute_omni_stats')
    omni_open_session_count = fields.Integer(
        string='Open Conversations', compute='_compute_omni_stats')
    omni_closed_session_count = fields.Integer(
        string='Closed Conversations', compute='_compute_omni_stats')
    omni_avg_response_seconds = fields.Float(
        string='Avg. Response Time (s)', compute='_compute_omni_stats')
    omni_call_count = fields.Integer(
        string='Total Calls', compute='_compute_omni_stats')
    omni_missed_call_count = fields.Integer(
        string='Missed Calls', compute='_compute_omni_stats')

    def _compute_omni_stats(self):
        Session = self.env['crm.chat.session']
        ResponseTime = self.env['crm.response.time']
        Call = self.env['crm.call.log']
        for user in self:
            sessions = Session.search([('agent_id', '=', user.id)])
            user.omni_assigned_session_count = len(sessions)
            user.omni_open_session_count = len(sessions.filtered(lambda s: s.state in ('new', 'open', 'pending')))
            user.omni_closed_session_count = len(sessions.filtered(lambda s: s.state == 'closed'))
            response_logs = ResponseTime.search([('agent_id', '=', user.id)])
            user.omni_avg_response_seconds = (
                sum(response_logs.mapped('response_seconds')) / len(response_logs)
                if response_logs else 0.0
            )
            calls = Call.search([('agent_id', '=', user.id)])
            user.omni_call_count = len(calls)
            user.omni_missed_call_count = len(calls.filtered(lambda c: c.state in ('missed', 'rejected')))
