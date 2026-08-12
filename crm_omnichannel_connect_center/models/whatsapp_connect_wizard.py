# -*- coding: utf-8 -*-
import re
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WhatsappConnectWizard(models.TransientModel):
    """'Add Number' flow: fill a label, hit Start Pairing, scan the QR shown
    live in this same screen (auto-refreshed by static/src/js/wa_qr_live.js).
    Each run of this wizard creates one crm.channel - run it again to add
    another WhatsApp number."""
    _name = 'whatsapp.connect.wizard'
    _description = 'Connect a WhatsApp Number (QR pairing)'

    name = fields.Char(string='Label', required=True, default=_('WhatsApp Number'),
                        help='Internal name, e.g. "Sales WhatsApp" or "Support Line 2".')
    bridge_base_url = fields.Char(string='Bridge URL', required=True)
    bridge_api_key = fields.Char(string='Bridge API Key', required=True)
    session_id = fields.Char(string='Session ID', required=True)

    channel_id = fields.Many2one('crm.channel', string='Channel', readonly=True)
    connection_state = fields.Selection(related='channel_id.baileys_connection_state', readonly=True)
    qr_image = fields.Binary(related='channel_id.baileys_qr_image', readonly=True)
    connected_number = fields.Char(related='channel_id.baileys_connected_number', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        icp = self.env['ir.config_parameter'].sudo()
        res.setdefault('bridge_base_url', icp.get_param('crm_omnichannel_connect_center.baileys_default_url', ''))
        res.setdefault('bridge_api_key', icp.get_param('crm_omnichannel_connect_center.baileys_default_api_key', ''))
        res.setdefault('session_id', f'wa-{uuid.uuid4().hex[:8]}')
        return res

    def action_start_pairing(self):
        """Create (or reuse) the crm.channel for this wizard run, kick off
        pairing on the bridge, and reopen the wizard so the embedded QR
        widget starts polling immediately."""
        self.ensure_one()
        if not (self.bridge_base_url and self.bridge_api_key and self.session_id):
            raise UserError(_('Bridge URL, API Key and Session ID are all required.'))
        if not re.match(r'^[a-zA-Z0-9_.-]+$', self.session_id):
            raise UserError(_('Session ID can only contain letters, numbers, dashes, dots and underscores.'))

        if not self.channel_id:
            existing = self.env['crm.channel'].search([('baileys_session_id', '=', self.session_id)], limit=1)
            channel = existing or self.env['crm.channel'].create({
                'name': self.name,
                'code': 'whatsapp',
                'icon': 'fa-whatsapp',
            })
            channel.write({
                'whatsapp_provider': 'baileys',
                'baileys_base_url': self.bridge_base_url,
                'baileys_api_key': self.bridge_api_key,
                'baileys_session_id': self.session_id,
            })
            self.channel_id = channel.id

        self.channel_id.action_baileys_start_pairing()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.connect.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context, wa_wizard_polling=True),
        }

    def action_refresh_status(self):
        """Called repeatedly by the front-end QR widget - cheap status poll,
        never raises to the UI."""
        self.ensure_one()
        if self.channel_id:
            self.channel_id.action_baileys_refresh_status()
        return {
            'state': self.connection_state,
            'has_qr': bool(self.qr_image),
            'connected_number': self.connected_number,
        }

    def action_done(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
