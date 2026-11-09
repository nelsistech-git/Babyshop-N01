# -*- coding: utf-8 -*-
from odoo import models, fields


class RealEstateBookingAgentLink(models.Model):
    _inherit = 'real.estate.booking'

    agent_id = fields.Many2one(
        'res.partner', string='Sold By (Agent / Referrer)', index=True, ondelete='restrict',
        help='Copied to the Sale Agreement, where the commission is generated.')
