# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CrmOmniUtils(models.AbstractModel):
    _name = 'crm.omni.utils'
    _description = 'Omni-Channel Shared Automation Helpers'

    @api.model
    def find_or_create_partner(self, name=None, phone=None, email=None,
                                external_identifier=None, channel=None):
        """Search for an existing customer by phone / email / external ID,
        or create a new one. Runs as sudo so any agent can trigger it
        regardless of their personal Contacts permissions."""
        Partner = self.env['res.partner'].sudo()
        partner = Partner
        if phone:
            partner = Partner.search([('phone', '=', phone)], limit=1) \
                or Partner.search([('mobile', '=', phone)], limit=1)
        if not partner and email:
            partner = Partner.search([('email', '=', email)], limit=1)
        if not partner and external_identifier:
            partner = Partner.search([('comment', 'like', external_identifier)], limit=1)
        if not partner:
            comment = False
            if external_identifier:
                channel_name = channel.name if channel else _('Omni-Channel')
                comment = _('%(channel)s ID: %(identifier)s') % {
                    'channel': channel_name, 'identifier': external_identifier}
            partner = Partner.create({
                'name': name or external_identifier or phone or _('New Contact'),
                'phone': phone,
                'email': email,
                'comment': comment,
            })
        return partner

    @api.model
    def find_or_create_lead(self, partner, channel=None, agent=None, team=None, priority='1'):
        """Search for an open lead/opportunity for this partner, or create one."""
        Lead = self.env['crm.lead'].sudo()
        lead = Lead.search([
            ('partner_id', '=', partner.id),
            ('type', 'in', ('lead', 'opportunity')),
            ('active', '=', True),
        ], limit=1)
        if not lead:
            channel_name = channel.name if channel else _('Omni-Channel')
            lead = Lead.create({
                'name': _('%(channel)s - %(name)s') % {'channel': channel_name, 'name': partner.name},
                'partner_id': partner.id,
                'phone': partner.phone,
                'email_from': partner.email,
                'user_id': agent.id if agent else False,
                'team_id': team.id if team else False,
                'source_id': self.get_utm_source(channel).id,
                'medium_id': self.get_utm_medium().id,
                'priority': priority or '0',
            })
        return lead

    @api.model
    def get_utm_source(self, channel=None):
        name = channel.name if channel else 'Omni-Channel'
        source = self.env['utm.source'].sudo().search([('name', '=', name)], limit=1)
        if not source:
            source = self.env['utm.source'].sudo().create({'name': name})
        return source

    @api.model
    def get_utm_medium(self):
        medium = self.env['utm.medium'].sudo().search([('name', '=', 'Omni-Channel Hub')], limit=1)
        if not medium:
            medium = self.env['utm.medium'].sudo().create({'name': 'Omni-Channel Hub'})
        return medium

    @api.model
    def assign_next_agent(self, config_key):
        """Generic round-robin picker across the Omni-Channel Agent group,
        keyed by a caller-supplied ir.config_parameter key so different
        work queues (chats vs. calls) rotate independently."""
        group = self.env.ref('crm_omnichannel_hub.group_omni_agent', raise_if_not_found=False)
        if not group:
            return self.env['res.users']
        agents = group.sudo().users.filtered(lambda u: u.active).sorted('id')
        if not agents:
            return self.env['res.users']
        param = self.env['ir.config_parameter'].sudo()
        last_agent_id = int(param.get_param(config_key, default='0') or 0)
        agent_ids = agents.ids
        if last_agent_id in agent_ids:
            next_index = (agent_ids.index(last_agent_id) + 1) % len(agent_ids)
        else:
            next_index = 0
        next_agent = self.env['res.users'].browse(agent_ids[next_index])
        param.set_param(config_key, str(next_agent.id))
        return next_agent
