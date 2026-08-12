# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    facebook_id = fields.Char(string='Facebook ID')
    instagram_id = fields.Char(string='Instagram ID')
    whatsapp_number = fields.Char(string='WhatsApp Number')
    call_number = fields.Char(string='Call Number')

    communication_ids = fields.One2many('crm.communication', 'lead_id', string='Communications')
    chat_session_ids = fields.One2many('crm.chat.session', 'lead_id', string='Conversations')
    call_log_ids = fields.One2many('crm.call.log', 'lead_id', string='Calls')

    communication_count = fields.Integer(compute='_compute_communication_count', string='Communications')
    chat_session_count = fields.Integer(compute='_compute_communication_count', string='Conversations')
    call_log_count = fields.Integer(compute='_compute_communication_count', string='Calls')

    @api.depends('communication_ids', 'chat_session_ids', 'call_log_ids')
    def _compute_communication_count(self):
        for lead in self:
            lead.communication_count = len(lead.communication_ids)
            lead.chat_session_count = len(lead.chat_session_ids)
            lead.call_log_count = len(lead.call_log_ids)

    def action_view_call_logs(self):
        self.ensure_one()
        return {
            'name': 'Calls',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.call.log',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }

    def action_click_to_call(self):
        self.ensure_one()
        return self.env['crm.call.log'].action_click_to_call(
            partner_id=self.partner_id.id if self.partner_id else None,
            phone_number=self.phone or self.mobile,
        )

    def action_view_chat_sessions(self):
        self.ensure_one()
        return {
            'name': 'Conversations',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.chat.session',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }

    def action_view_communications(self):
        self.ensure_one()
        return {
            'name': 'Communication Timeline',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.communication',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }
