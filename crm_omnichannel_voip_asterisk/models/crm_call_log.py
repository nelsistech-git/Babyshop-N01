# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class CrmCallLog(models.Model):
    _inherit = 'crm.call.log'

    asterisk_uniqueid = fields.Char(string='Asterisk Unique ID', index=True, copy=False,
                                     help='Correlates this record with the Asterisk channel(s) '
                                          'for the call, so live AMI events can update it.')
    asterisk_agent_channel = fields.Char(string='Agent Channel', copy=False,
                                          help='e.g. PJSIP/1001-000001a2 - the leg Asterisk opened toward the agent.')

    @api.model
    def action_click_to_call(self, partner_id=None, phone_number=None):
        result = super().action_click_to_call(partner_id=partner_id, phone_number=phone_number)
        call = self.browse(result.get('res_id'))
        if call:
            call._originate_via_asterisk()
        return result

    def _originate_via_asterisk(self):
        """Ask Asterisk to ring the agent's extension first; once they pick
        up, Asterisk dials the customer's number out through the configured
        trunk. Live status after this point comes from ami_bridge.py events,
        not from this synchronous call."""
        self.ensure_one()
        channel = self.channel_id
        agent = self.agent_id
        if not (channel.ami_host and channel.ami_username and channel.ami_secret):
            _logger.info('Call %s: channel %s has no AMI credentials configured; '
                         'record created but not auto-dialed.', self.id, channel.name)
            return
        if not (agent and agent.voip_extension):
            self.message_post(body=_('Cannot auto-dial: agent has no VoIP Extension configured on their user profile.'))
            return
        if not self.phone_number:
            return

        from .asterisk_ami import AsteriskAMI, AsteriskAMIError
        # Note: routing to the actual trunk (channel.ami_trunk) happens in
        # your Asterisk dialplan at [context]/[extension] - Originate here
        # only tells Asterisk "ring the agent, then run the dialplan at
        # context/extension for the customer leg", same as picking up a
        # deskphone and dialing the number by hand. ami_trunk is exposed on
        # the channel as a reference value for whoever writes that dialplan.
        try:
            with AsteriskAMI(channel.ami_host, channel.ami_port, channel.ami_username,
                              channel.ami_secret, timeout=8) as ami:
                agent_channel = f'PJSIP/{agent.voip_extension}'
                response = ami.originate(
                    channel=agent_channel,
                    context=channel.ami_context or 'from-internal',
                    extension=self.phone_number,
                    priority=1,
                    caller_id=f'{agent.name} <{agent.voip_extension}>',
                    variables={'QUICKCRM_CALL_ID': str(self.id)},
                )
            self.sudo().write({
                'asterisk_agent_channel': agent_channel,
                'asterisk_uniqueid': response.get('Uniqueid') or response.get('ActionID') or False,
            })
        except AsteriskAMIError as exc:
            _logger.warning('Asterisk originate failed for call %s: %s', self.id, exc)
            self.message_post(body=_('Could not originate call via Asterisk: %s') % exc)
        except Exception:
            _logger.exception('Unexpected error originating call %s via Asterisk', self.id)
            self.message_post(body=_('Could not originate call via Asterisk - see server log.'))

    # =====================================================================
    # Called by the /omni/webhook/asterisk controller for every AMI event
    # relayed by bridge/ami_bridge.py, keyed by QUICKCRM_CALL_ID when we
    # originated the call ourselves, or by phone number for inbound calls
    # Asterisk received on its own (no matching crm.call.log yet).
    # =====================================================================
    @api.model
    def _asterisk_sync_event(self, channel, event_vals):
        # Both lookups are scoped to this channel's own calls: the webhook is
        # only authenticated per-channel (shared secret), so an id/uniqueid
        # that happens to belong to a *different* channel's call must never
        # be readable or writable from here.
        call_id = event_vals.get('quickcrm_call_id')
        call = self.env['crm.call.log']
        if call_id:
            try:
                call_id = int(call_id)
            except (TypeError, ValueError):
                call_id = None
            if call_id:
                call = self.search([('id', '=', call_id), ('channel_id', '=', channel.id)], limit=1)
        if not call:
            uniqueid = event_vals.get('uniqueid')
            call = self.search([
                ('asterisk_uniqueid', '=', uniqueid), ('channel_id', '=', channel.id),
            ], limit=1) if uniqueid else self.env['crm.call.log']

        event = event_vals.get('event')
        if not call and event == 'ring' and event_vals.get('caller_number'):
            # Genuinely new inbound call Asterisk didn't get from us - create it.
            call = self.create({
                'channel_id': channel.id,
                'direction': 'inbound',
                'phone_number': event_vals['caller_number'],
                'state': 'ringing',
                'asterisk_uniqueid': event_vals.get('uniqueid'),
            })
        if not call:
            return

        if event == 'ring':
            if call.state == 'new':
                call.write({'state': 'ringing'})
        elif event == 'answer':
            call.action_answer() if call.state != 'answered' else None
        elif event == 'hold':
            if call.state != 'on_hold':
                call.action_hold()
        elif event == 'unhold':
            call.write({'state': 'answered'})
        elif event == 'hangup':
            if call.state in ('new', 'ringing'):
                call.action_mark_missed()
            elif call.state != 'completed':
                call.action_complete()
        elif event == 'recording_ready' and event_vals.get('recording_url'):
            self.env['crm.call.recording'].sudo().create({
                'call_id': call.id,
                'recording_url': event_vals['recording_url'],
            })
