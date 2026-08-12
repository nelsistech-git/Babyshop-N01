# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    voip_extension = fields.Char(string='VoIP Username / Extension Number')
    voip_sip_auth_username = fields.Char(string='SIP Auth Username')
    voip_sip_secret = fields.Char(string='VoIP Secret')
    voip_call_from_another_device = fields.Boolean(string='Call From Another Device')
    voip_external_device_number = fields.Char(string='External Device Number')
    voip_reject_incoming_calls = fields.Boolean(string='Reject Incoming Calls')
