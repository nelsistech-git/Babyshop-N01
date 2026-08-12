# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import timedelta


class CrmChatSession(models.Model):
    _name = 'crm.chat.session'
    _description = 'Omni-Channel Conversation (Unified Inbox)'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'crm.csat.mixin']
    _order = 'last_message_date desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    # --- Customer / identity -------------------------------------------------
    channel_id = fields.Many2one('crm.channel', string='Channel', required=True,
                                  tracking=True, index=True)
    channel_code = fields.Selection(related='channel_id.code', store=True, string='Channel Type')
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True, index=True)
    partner_name = fields.Char(string='Customer Name (as received)')
    partner_phone = fields.Char(string='Phone')
    partner_email = fields.Char(string='Email')
    external_identifier = fields.Char(
        string='External ID',
        help='Facebook PSID / Instagram ID / WhatsApp number / Caller number, depending on channel.')
    lead_id = fields.Many2one('crm.lead', string='CRM Lead', tracking=True, index=True)

    # --- Assignment / state ---------------------------------------------------
    agent_id = fields.Many2one('res.users', string='Assigned Agent', tracking=True, index=True)
    team_id = fields.Many2one('crm.team', string='Sales Team',
                               default=lambda self: self.env['crm.team'].search(
                                   [('company_id', 'in', [self.env.company.id, False])], limit=1))
    state = fields.Selection([
        ('new', 'New'),
        ('open', 'Open'),
        ('pending', 'Pending'),
        ('closed', 'Closed'),
        ('spam', 'Spam'),
    ], default='new', required=True, tracking=True, index=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], default='1', tracking=True)
    tag_ids = fields.Many2many('crm.communication.tag', string='Tags')
    is_starred = fields.Boolean(string='Starred', default=False)

    # --- Messages ---------------------------------------------------------
    message_line_ids = fields.One2many('crm.chat.message', 'session_id', string='Messages')
    last_message_date = fields.Datetime(string='Last Message', default=fields.Datetime.now, index=True)
    last_message_preview = fields.Char(string='Last Message Preview')
    is_unread = fields.Boolean(string='Unread', default=True, index=True)
    unread_count = fields.Integer(string='Unread Count', default=0)

    # --- SLA ---------------------------------------------------------
    sla_id = fields.Many2one('crm.sla', string='SLA Policy')
    first_response_deadline = fields.Datetime(string='Response Due By')
    first_response_date = fields.Datetime(string='First Response Date')
    waiting_since = fields.Datetime(string='Waiting Since')
    sla_status = fields.Selection([
        ('none', 'No Pending Response'),
        ('green', 'On Time'),
        ('yellow', 'At Risk'),
        ('red', 'Breached'),
    ], compute='_compute_sla_status', store=True, string='SLA Status')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    # =====================================================================
    # COMPUTE
    # =====================================================================
    @api.depends('partner_id', 'partner_name', 'channel_id')
    def _compute_display_name(self):
        for rec in self:
            name = rec.partner_id.name or rec.partner_name or _('Unknown Contact')
            channel = rec.channel_id.name or ''
            rec.display_name = f'{name} - {channel}' if channel else name

    @api.depends('waiting_since', 'first_response_date', 'sla_id',
                 'sla_id.green_minutes', 'sla_id.yellow_minutes', 'sla_id.red_minutes')
    def _compute_sla_status(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.waiting_since or rec.first_response_date and rec.first_response_date >= rec.waiting_since:
                rec.sla_status = 'none'
                continue
            sla = rec.sla_id
            if not sla:
                rec.sla_status = 'none'
                continue
            elapsed_minutes = (now - rec.waiting_since).total_seconds() / 60.0
            if elapsed_minutes <= sla.green_minutes:
                rec.sla_status = 'green'
            elif elapsed_minutes <= sla.yellow_minutes:
                rec.sla_status = 'yellow'
            else:
                rec.sla_status = 'red'

    # =====================================================================
    # CRUD
    # =====================================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sla_id'):
                sla = self._get_default_sla(vals.get('channel_id'))
                if sla:
                    vals['sla_id'] = sla.id
        sessions = super().create(vals_list)
        for session in sessions:
            session._find_or_create_customer()
            if not session.agent_id:
                session._auto_assign_agent()
            session._find_or_create_lead()
            self.env['crm.communication'].sudo().create_from_session(session)
        return sessions

    def write(self, vals):
        res = super().write(vals)
        sync_fields = {'state', 'priority', 'tag_ids', 'last_message_date', 'lead_id', 'agent_id'}
        if sync_fields.intersection(vals.keys()):
            for session in self:
                self.env['crm.communication'].sudo().create_from_session(session)
        return res

    # =====================================================================
    # SLA / ROUND ROBIN HELPERS
    # =====================================================================
    def _get_default_sla(self, channel_id):
        domain = [('active', '=', True)]
        sla = self.env['crm.sla'].search(domain, limit=50)
        if not channel_id:
            return sla[:1]
        for policy in sla:
            if not policy.channel_ids or channel_id in policy.channel_ids.ids:
                return policy
        return self.env['crm.sla']

    def _auto_assign_agent(self):
        """Consult crm.assignment.rule first (keyword / VIP / working-hours /
        department routing); fall back to plain round-robin across the
        Omni-Channel Agent group if no rule matches."""
        for rec in self:
            message_body = self.env.context.get('first_message_body')
            agent, team = self.env['crm.assignment.rule'].sudo().resolve_agent(
                rec.channel_id, partner=rec.partner_id, message_body=message_body)
            if not agent:
                agent = rec._assign_next_agent()
            vals = {}
            if agent:
                vals['agent_id'] = agent.id
            if team and not rec.team_id:
                vals['team_id'] = team.id
            if vals:
                rec.sudo().write(vals)

    def _assign_next_agent(self):
        """Simple round-robin assignment across users in the Omni-Channel Agent group."""
        group = self.env.ref('crm_omnichannel_hub.group_omni_agent', raise_if_not_found=False)
        if not group:
            return self.env['res.users']
        agents = group.sudo().users.filtered(lambda u: u.active).sorted('id')
        if not agents:
            return self.env['res.users']
        param = self.env['ir.config_parameter'].sudo()
        last_agent_id = int(param.get_param('crm_omnichannel_hub.last_assigned_agent_id', default='0') or 0)
        agent_ids = agents.ids
        if last_agent_id in agent_ids:
            next_index = (agent_ids.index(last_agent_id) + 1) % len(agent_ids)
        else:
            next_index = 0
        next_agent = self.env['res.users'].browse(agent_ids[next_index])
        param.set_param('crm_omnichannel_hub.last_assigned_agent_id', str(next_agent.id))
        return next_agent

    def _compute_first_response_deadline(self):
        """Called when a new inbound (customer) message arrives."""
        for rec in self:
            now = fields.Datetime.now()
            vals = {'waiting_since': now}
            if rec.sla_id:
                vals['first_response_deadline'] = now + timedelta(minutes=rec.sla_id.red_minutes)
            if rec.state in ('closed', 'spam'):
                vals['state'] = 'open'
            rec.write(vals)

    def _mark_first_response(self, message):
        """Called when an outbound (agent) message is created."""
        for rec in self:
            vals = {'is_unread': False, 'unread_count': 0}
            if rec.waiting_since and (not rec.first_response_date or rec.first_response_date < rec.waiting_since):
                vals['first_response_date'] = message.message_date
                self.env['crm.response.time'].sudo().create({
                    'session_id': rec.id,
                    'agent_id': rec.agent_id.id or message.agent_id.id,
                    'channel_id': rec.channel_id.id,
                    'waiting_since': rec.waiting_since,
                    'response_date': message.message_date,
                })
            rec.write(vals)

    # =====================================================================
    # CRM AUTOMATION
    # =====================================================================
    def _find_or_create_customer(self):
        Partner = self.env['res.partner'].sudo()
        for rec in self:
            if rec.partner_id:
                continue
            partner = Partner
            if rec.partner_phone:
                partner = Partner.search([('phone', '=', rec.partner_phone)], limit=1) \
                    or Partner.search([('mobile', '=', rec.partner_phone)], limit=1)
            if not partner and rec.partner_email:
                partner = Partner.search([('email', '=', rec.partner_email)], limit=1)
            if not partner and rec.external_identifier:
                partner = Partner.search([('comment', 'like', rec.external_identifier)], limit=1)
            if not partner:
                partner = Partner.create({
                    'name': rec.partner_name or rec.external_identifier or _('New Contact'),
                    'phone': rec.partner_phone,
                    'email': rec.partner_email,
                    'comment': rec.external_identifier and
                    _('%(channel)s ID: %(identifier)s') % {
                        'channel': rec.channel_id.name, 'identifier': rec.external_identifier} or False,
                })
            rec.sudo().write({'partner_id': partner.id})

    def _find_or_create_lead(self):
        Lead = self.env['crm.lead'].sudo()
        for rec in self:
            if rec.lead_id or not rec.partner_id:
                continue
            lead = Lead.search([
                ('partner_id', '=', rec.partner_id.id),
                ('type', 'in', ('lead', 'opportunity')),
                ('active', '=', True),
            ], limit=1)
            if not lead:
                lead = Lead.create({
                    'name': _('%(channel)s - %(name)s') % {
                        'channel': rec.channel_id.name, 'name': rec.partner_id.name},
                    'partner_id': rec.partner_id.id,
                    'phone': rec.partner_phone or rec.partner_id.phone,
                    'email_from': rec.partner_email or rec.partner_id.email,
                    'user_id': rec.agent_id.id,
                    'team_id': rec.team_id.id if rec.team_id else False,
                    'source_id': rec._get_utm_source().id,
                    'medium_id': rec._get_utm_medium().id,
                    'priority': rec.priority or '0',
                })
            rec.sudo().write({'lead_id': lead.id})

    def _get_utm_source(self):
        source = self.env['utm.source'].sudo().search([('name', '=', self.channel_id.name)], limit=1)
        if not source:
            source = self.env['utm.source'].sudo().create({'name': self.channel_id.name or 'Omni-Channel'})
        return source

    def _get_utm_medium(self):
        medium = self.env['utm.medium'].sudo().search([('name', '=', 'Omni-Channel Hub')], limit=1)
        if not medium:
            medium = self.env['utm.medium'].sudo().create({'name': 'Omni-Channel Hub'})
        return medium

    # =====================================================================
    # ACTIONS
    # =====================================================================
    def action_mark_read(self):
        self.write({'is_unread': False, 'unread_count': 0})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reopen(self):
        self.write({'state': 'open'})

    def action_mark_spam(self):
        self.write({'state': 'spam'})

    def action_toggle_star(self):
        for rec in self:
            rec.is_starred = not rec.is_starred

    def action_convert_to_lead(self):
        """Manual fallback for the rare case a session has no lead yet
        (e.g. the customer record was linked after the fact). Normal flow
        already auto-creates the lead at session creation time."""
        for rec in self:
            if not rec.lead_id:
                rec._find_or_create_lead()

    def action_send_message(self):
        """Hook for the form view 'Send' button; expects body set via context or wizard in
        connector modules. Kept minimal here for the core module."""
        self.ensure_one()
        return True

    def action_view_lead(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': self.lead_id.id,
            'target': 'current',
        }

    # =====================================================================
    # SLA ESCALATION (CRON)
    # =====================================================================
    @api.model
    def _cron_check_sla_escalation(self):
        """Notify escalation users for any conversation that has breached its
        SLA (red) and is still awaiting a first response."""
        sessions = self.search([
            ('sla_status', '=', 'red'),
            ('state', 'in', ('new', 'open', 'pending')),
        ])
        for session in sessions:
            escalate_users = session.sla_id.escalate_user_ids
            if not escalate_users:
                continue
            note = _(
                'SLA breached for conversation with %(partner)s on %(channel)s. '
                'Waiting since %(since)s.'
            ) % {
                'partner': session.partner_id.name or session.partner_name or _('Unknown'),
                'channel': session.channel_id.name,
                'since': session.waiting_since,
            }
            session.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('SLA Breach - Immediate Attention Required'),
                note=note,
                user_id=escalate_users[0].id,
            )
            session.message_post(
                body=note,
                partner_ids=escalate_users.mapped('partner_id').ids,
            )
