# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CrmCommunication(models.Model):
    _name = 'crm.communication'
    _description = 'Unified Communication Record (CRM Timeline Entry)'
    _order = 'date desc, id desc'
    _rec_name = 'subject'

    comm_type = fields.Selection([
        ('chat', 'Chat / Message'),
        ('call', 'Call'),
    ], required=True, default='chat', index=True)
    subject = fields.Char(string='Subject', required=True)
    lead_id = fields.Many2one('crm.lead', string='CRM Lead', required=True,
                               ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string='Customer', index=True)
    channel_id = fields.Many2one('crm.channel', string='Channel', index=True)
    agent_id = fields.Many2one('res.users', string='Agent', index=True)
    session_id = fields.Many2one('crm.chat.session', string='Related Conversation',
                                  ondelete='cascade')
    call_id = fields.Many2one('crm.call.log', string='Related Call',
                               ondelete='cascade')
    state = fields.Char(string='Status')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], default='1')
    tag_ids = fields.Many2many('crm.communication.tag', string='Tags')
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True, index=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def create_from_session(self, session):
        """Create (or refresh) the timeline record that mirrors a chat session."""
        existing = self.search([('session_id', '=', session.id)], limit=1)
        vals = {
            'comm_type': 'chat',
            'subject': session.display_name,
            'lead_id': session.lead_id.id,
            'partner_id': session.partner_id.id,
            'channel_id': session.channel_id.id,
            'agent_id': session.agent_id.id,
            'session_id': session.id,
            'state': dict(session._fields['state'].selection).get(session.state),
            'priority': session.priority,
            'tag_ids': [(6, 0, session.tag_ids.ids)],
            'date': session.last_message_date or fields.Datetime.now(),
        }
        if existing:
            existing.write(vals)
            return existing
        if not session.lead_id:
            return self.env['crm.communication']
        return self.create(vals)

    @api.model
    def create_from_call(self, call):
        """Create (or refresh) the timeline record that mirrors a call log."""
        existing = self.search([('call_id', '=', call.id)], limit=1)
        vals = {
            'comm_type': 'call',
            'subject': call.display_name,
            'lead_id': call.lead_id.id,
            'partner_id': call.partner_id.id,
            'channel_id': call.channel_id.id,
            'agent_id': call.agent_id.id,
            'call_id': call.id,
            'state': dict(call._fields['state'].selection).get(call.state),
            'priority': call.priority,
            'tag_ids': [(6, 0, call.tag_ids.ids)],
            'date': call.call_date or fields.Datetime.now(),
        }
        if existing:
            existing.write(vals)
            return existing
        if not call.lead_id:
            return self.env['crm.communication']
        return self.create(vals)
