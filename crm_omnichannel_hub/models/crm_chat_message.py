# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmChatMessage(models.Model):
    _name = 'crm.chat.message'
    _description = 'Omni-Channel Chat Message'
    _order = 'message_date asc, id asc'
    _rec_name = 'body'

    session_id = fields.Many2one('crm.chat.session', string='Conversation',
                                  required=True, ondelete='cascade', index=True)
    channel_id = fields.Many2one(related='session_id.channel_id', store=True, string='Channel')
    direction = fields.Selection([
        ('in', 'Incoming (Customer)'),
        ('out', 'Outgoing (Agent)'),
        ('note', 'Internal Note'),
    ], string='Direction', required=True, default='in')
    author_id = fields.Many2one('res.partner', string='Author (Customer)')
    agent_id = fields.Many2one('res.users', string='Agent',
                                default=lambda self: self.env.user)
    body = fields.Text(string='Message')
    message_type = fields.Selection([
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Voice/Audio'),
        ('document', 'Document'),
        ('location', 'Location'),
        ('contact', 'Contact Card'),
        ('sticker', 'Sticker'),
        ('template', 'Template Message'),
    ], string='Message Type', default='text', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    external_message_id = fields.Char(string='External Message ID',
                                       help='ID of this message on the source platform (used to prevent duplicate sync).')
    message_date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    is_read = fields.Boolean(string='Read', default=False)
    is_delivered = fields.Boolean(string='Delivered', default=True)
    is_seen = fields.Boolean(string='Seen', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        for message in messages:
            session = message.session_id
            if message.direction == 'in':
                session.write({
                    'last_message_date': message.message_date,
                    'last_message_preview': (message.body or '')[:150],
                    'is_unread': True,
                    'unread_count': session.unread_count + 1,
                })
                session._compute_first_response_deadline()
            elif message.direction == 'out':
                session.write({
                    'last_message_date': message.message_date,
                    'last_message_preview': (message.body or '')[:150],
                })
                session._mark_first_response(message)
        return messages
