# -*- coding: utf-8 -*-
from datetime import datetime, time

from odoo import api, fields, models


class CrmOmniDashboard(models.AbstractModel):
    _name = 'crm.omni.dashboard'
    _description = 'Omni-Channel Dashboard Data Provider'

    @api.model
    def _today_start(self):
        return datetime.combine(fields.Date.context_today(self), time.min)

    # =====================================================================
    # EXECUTIVE DASHBOARD
    # =====================================================================
    @api.model
    def get_executive_dashboard(self):
        Session = self.env['crm.chat.session'].sudo()
        Lead = self.env['crm.lead'].sudo()
        today_start = self._today_start()

        sessions_today = Session.search_count([('create_date', '>=', today_start)])
        leads_today = Lead.search([('create_date', '>=', today_start)])
        won_today = leads_today.filtered(lambda l: l.stage_id.is_won)
        lost_today = leads_today.filtered(lambda l: not l.active and l.probability == 0)

        total_conversations = Session.search_count([])
        open_conversations = Session.search_count([('state', 'in', ('new', 'open', 'pending'))])
        sla_breaches = Session.search_count([('sla_status', '=', 'red')])

        Call = self.env['crm.call.log'].sudo()
        calls_today = Call.search([('create_date', '>=', today_start)])
        missed_calls_today = calls_today.filtered(lambda c: c.state in ('missed', 'rejected'))

        revenue_won_today = sum(won_today.mapped('expected_revenue'))

        rated_sessions = Session.search([('customer_rating', '!=', False)])
        rated_calls = Call.search([('customer_rating', '!=', False)])
        all_ratings = [int(r) for r in rated_sessions.mapped('customer_rating')] + \
                       [int(r) for r in rated_calls.mapped('customer_rating')]
        avg_csat = round(sum(all_ratings) / len(all_ratings), 2) if all_ratings else 0.0

        channel_breakdown = {}
        for channel in self.env['crm.channel'].sudo().search([]):
            channel_breakdown[channel.name] = Session.search_count([
                ('channel_id', '=', channel.id), ('create_date', '>=', today_start)])

        return {
            'today_leads': len(leads_today),
            'today_chats': sessions_today,
            'today_calls': len(calls_today),
            'today_missed_calls': len(missed_calls_today),
            'today_won': len(won_today),
            'today_lost': len(lost_today),
            'today_revenue_won': revenue_won_today,
            'total_conversations': total_conversations,
            'open_conversations': open_conversations,
            'sla_breaches': sla_breaches,
            'conversion_rate': round((len(won_today) / len(leads_today) * 100), 1) if leads_today else 0.0,
            'avg_csat': avg_csat,
            'channel_breakdown': channel_breakdown,
        }

    # =====================================================================
    # MANAGER DASHBOARD
    # =====================================================================
    @api.model
    def get_manager_dashboard(self):
        Session = self.env['crm.chat.session'].sudo()
        group = self.env.ref('crm_omnichannel_hub.group_omni_agent', raise_if_not_found=False)
        agents = group.sudo().users if group else self.env['res.users']

        waiting_chats = Session.search_count([
            ('state', 'in', ('new', 'open', 'pending')), ('is_unread', '=', True)])
        sla_breaches = Session.search_count([('sla_status', '=', 'red')])
        online_agents = agents.filtered(lambda u: u.active)

        leaderboard = []
        for agent in agents:
            leaderboard.append({
                'id': agent.id,
                'name': agent.name,
                'assigned': agent.omni_assigned_session_count,
                'open': agent.omni_open_session_count,
                'closed': agent.omni_closed_session_count,
                'avg_response': round(agent.omni_avg_response_seconds, 1),
                'calls': agent.omni_call_count,
                'missed_calls': agent.omni_missed_call_count,
            })
        leaderboard.sort(key=lambda row: row['closed'], reverse=True)

        return {
            'waiting_chats': waiting_chats,
            'sla_breaches': sla_breaches,
            'agent_count': len(online_agents),
            'leaderboard': leaderboard,
        }

    # =====================================================================
    # AGENT DASHBOARD
    # =====================================================================
    @api.model
    def get_agent_dashboard(self):
        user = self.env.user
        Session = self.env['crm.chat.session']
        today_start = self._today_start()

        my_sessions = Session.search([('agent_id', '=', user.id)])
        today_sessions = my_sessions.filtered(lambda s: s.create_date and s.create_date >= today_start)

        return {
            'unread': len(my_sessions.filtered(lambda s: s.is_unread)),
            'pending': len(my_sessions.filtered(lambda s: s.state == 'pending')),
            'today_chats': len(today_sessions),
            'open': len(my_sessions.filtered(lambda s: s.state in ('new', 'open', 'pending'))),
            'closed': len(my_sessions.filtered(lambda s: s.state == 'closed')),
            'sla_breaches': len(my_sessions.filtered(lambda s: s.sla_status == 'red')),
            'avg_response': round(user.omni_avg_response_seconds, 1),
            'calls': user.omni_call_count,
            'missed_calls': user.omni_missed_call_count,
        }
