# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmChannel(models.Model):
    _inherit = 'crm.channel'

    # --- Asterisk Manager Interface (AMI) - used to originate calls -----------
    ami_host = fields.Char(string='AMI Host', help='Hostname or IP of the Asterisk server.')
    ami_port = fields.Integer(string='AMI Port', default=5038)
    ami_username = fields.Char(string='AMI Username')
    ami_secret = fields.Char(string='AMI Secret', groups='crm_omnichannel_hub.group_omni_manager')
    ami_context = fields.Char(string='Originate Context', default='from-internal',
                               help='Dialplan context used when originating outbound calls.')
    ami_trunk = fields.Char(string='Outbound Trunk/Gateway', help='e.g. PJSIP/my-trunk - prefixed to '
                             'the dialed number when originating (Dial(PJSIP/<number>@<trunk>)).')

    # --- SIP / WebRTC (agent softphone) - same fields as Odoo's built-in ------
    # VoIP settings screen (OnSIP Domain / WebSocket / Environment), kept here
    # so every field needed to configure calling lives on one channel record.
    sip_domain = fields.Char(string='SIP / OnSIP Domain')
    sip_websocket_url = fields.Char(string='WebSocket URL', help='wss://... used by the browser softphone (WebRTC).')
    voip_environment = fields.Selection([
        ('demo', 'Demo'),
        ('production', 'Production'),
    ], string='VoIP Environment', default='production')

    # --- Bridge webhook (Asterisk events -> Odoo) -------------------------
    ami_webhook_url = fields.Char(string='Inbound Event Webhook URL (give this to ami_bridge.py)',
                                   compute='_compute_ami_webhook_url')
    ami_webhook_secret = fields.Char(string='Webhook Shared Secret',
                                      groups='crm_omnichannel_hub.group_omni_manager')

    @api.depends('name')
    def _compute_ami_webhook_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.ami_webhook_url = f'{base_url}/omni/webhook/asterisk'

    def action_test_ami_connection(self):
        """Quick synchronous AMI login/logoff, just to confirm the credentials
        and reachability - does not originate a call."""
        self.ensure_one()
        if not (self.ami_host and self.ami_username and self.ami_secret):
            raise UserError(_('Set AMI Host, Username and Secret first.'))
        from .asterisk_ami import AsteriskAMI
        try:
            with AsteriskAMI(self.ami_host, self.ami_port, self.ami_username, self.ami_secret, timeout=6):
                pass
        except Exception as exc:
            raise UserError(_('Could not connect: %s') % exc)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': _('Success'), 'message': _('AMI login succeeded.'), 'sticky': False},
        }
