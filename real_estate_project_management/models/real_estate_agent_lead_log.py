# -*- coding: utf-8 -*-
from odoo import models, fields


class RealEstateAgentLeadLog(models.Model):
    """A call / meeting / visit note against a CRM lead."""
    _name = 'real.estate.agent.lead.log'
    _description = 'Agent CRM Interaction Log'
    _order = 'date desc, id desc'

    lead_id = fields.Many2one('real.estate.agent.lead', string='Lead', required=True,
                               ondelete='cascade', index=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    interaction_type = fields.Selection([
        ('call', 'Phone Call'),
        ('whatsapp', 'WhatsApp / SMS'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('site_visit', 'Site Visit'),
        ('other', 'Other'),
    ], string='Type', default='call', required=True)
    note = fields.Text(string='What was discussed', required=True)
    user_id = fields.Many2one('res.users', string='Logged By', default=lambda self: self.env.user,
                               readonly=True)
