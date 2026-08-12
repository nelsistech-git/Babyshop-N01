# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmQuickReply(models.Model):
    _name = 'crm.quick.reply'
    _description = 'Quick Reply / Canned Response'
    _order = 'sequence, id'

    name = fields.Char(string='Shortcut', required=True, help='Short keyword used to trigger this template, e.g. /thanks')
    title = fields.Char(string='Title', required=True)
    message = fields.Text(string='Message', required=True)
    channel_ids = fields.Many2many('crm.channel', string='Applicable Channels',
                                    help='Leave empty to make available on all channels.')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
