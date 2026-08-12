# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VoipConnectWizard(models.TransientModel):
    """'Add Calling Line' flow: fill in AMI + SIP details (pre-filled from
    Settings defaults if set), hit Test & Connect - this runs the same
    two-part check as the dashboard's Test Connection button (AMI login +
    bridge health) BEFORE saving, then creates the crm.channel record only
    if at least the AMI login succeeded."""
    _name = 'voip.connect.wizard'
    _description = 'Connect a VoIP Calling Line (Asterisk)'

    name = fields.Char(string='Label', required=True, default=_('IP Calling'),
                        help='Internal name, e.g. "Sales Line" or "Support Queue".')

    ami_host = fields.Char(string='AMI Host', required=True)
    ami_port = fields.Integer(string='AMI Port', default=5038, required=True)
    ami_username = fields.Char(string='AMI Username', required=True)
    ami_secret = fields.Char(string='AMI Secret', required=True)
    ami_context = fields.Char(string='Originate Context', default='from-internal')
    ami_trunk = fields.Char(string='Outbound Trunk/Gateway')

    sip_domain = fields.Char(string='SIP / OnSIP Domain')
    sip_websocket_url = fields.Char(string='WebSocket URL')
    voip_environment = fields.Selection([
        ('demo', 'Demo'), ('production', 'Production'),
    ], string='VoIP Environment', default='production')

    ami_webhook_secret = fields.Char(string='Webhook Shared Secret',
                                      help='Any random string - must match ODOO_WEBHOOK_SECRET on ami_bridge.py.')

    channel_id = fields.Many2one('crm.channel', string='Channel', readonly=True)
    result_message = fields.Char(readonly=True)
    result_success = fields.Boolean(readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        icp = self.env['ir.config_parameter'].sudo()
        res.setdefault('ami_host', icp.get_param('crm_omnichannel_connect_center.ami_default_host', ''))
        res.setdefault('ami_port', int(icp.get_param('crm_omnichannel_connect_center.ami_default_port', 5038) or 5038))
        res.setdefault('ami_username', icp.get_param('crm_omnichannel_connect_center.ami_default_username', ''))
        res.setdefault('ami_secret', icp.get_param('crm_omnichannel_connect_center.ami_default_secret', ''))
        import secrets
        res.setdefault('ami_webhook_secret', secrets.token_urlsafe(18))
        return res

    def action_test_and_connect(self):
        """Verify AMI login (and bridge health, if configured) BEFORE
        creating/updating the crm.channel record, so a bad password never
        even gets saved as if it were working."""
        self.ensure_one()
        if not (self.ami_host and self.ami_username and self.ami_secret):
            raise UserError(_('AMI Host, Username and Secret are all required.'))

        from odoo.addons.crm_omnichannel_voip_asterisk.models.asterisk_ami import AsteriskAMI, AsteriskAMIError
        try:
            with AsteriskAMI(self.ami_host, self.ami_port, self.ami_username, self.ami_secret, timeout=6):
                pass
        except AsteriskAMIError as e:
            self.write({'result_success': False, 'result_message': _('AMI login failed: %s') % e})
            return self._reopen()
        except OSError as e:
            self.write({'result_success': False,
                        'result_message': _('Could not reach %s:%s: %s') % (self.ami_host, self.ami_port, e)})
            return self._reopen()

        channel = self.channel_id
        vals = {
            'name': self.name,
            'code': 'call',
            'icon': 'fa-phone',
            'ami_host': self.ami_host,
            'ami_port': self.ami_port,
            'ami_username': self.ami_username,
            'ami_secret': self.ami_secret,
            'ami_context': self.ami_context,
            'ami_trunk': self.ami_trunk,
            'sip_domain': self.sip_domain,
            'sip_websocket_url': self.sip_websocket_url,
            'voip_environment': self.voip_environment,
            'ami_webhook_secret': self.ami_webhook_secret,
        }
        if channel:
            channel.write(vals)
        else:
            channel = self.env['crm.channel'].create(vals)
        self.channel_id = channel.id

        bridge_url = self.env['ir.config_parameter'].sudo().get_param(
            'crm_omnichannel_connect_center.ami_bridge_health_url')
        message = _('AMI login succeeded and the calling line was saved.')
        if bridge_url:
            import requests
            try:
                data = requests.get(f'{bridge_url.rstrip("/")}/health', timeout=8).json()
                if data.get('ami_connected'):
                    message = _('Fully connected - AMI login OK, event bridge is live, and the line was saved.')
                else:
                    message = _('Saved, but the event bridge is running and NOT linked to Asterisk yet - '
                                 'check its logs. Outbound calls will still work.')
            except requests.exceptions.RequestException:
                message = _('Saved, but could not reach the event bridge health check at %s - live call status '
                             'sync will not work until it is running.') % bridge_url

        self.write({'result_success': True, 'result_message': message})
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'voip.connect.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_done(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
