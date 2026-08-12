# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmChannel(models.Model):
    _name = 'crm.channel'
    _description = 'Omni-Channel Communication Channel'
    _order = 'sequence, id'

    name = fields.Char(string='Channel Name', required=True)
    code = fields.Selection([
        ('facebook', 'Facebook Messenger'),
        ('instagram', 'Instagram'),
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('email', 'Email'),
        ('call', 'IP Calling'),
        ('other', 'Other'),
    ], string='Channel Type', required=True, default='other')
    icon = fields.Char(string='Icon (Font Awesome class)', default='fa-comments')
    color = fields.Integer(string='Color Index', default=0)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    account_identifier = fields.Char(
        string='Connected Account',
        help='Page / Account / Number connected for this channel instance '
             '(e.g. WhatsApp number, Facebook Page name). Populated by the '
             'relevant connector module.')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A channel with this name already exists.'),
    ]
