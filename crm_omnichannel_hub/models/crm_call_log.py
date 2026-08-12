# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CrmCallLog(models.Model):
    _name = 'crm.call.log'
    _description = 'IP Call Log'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'crm.csat.mixin']
    _order = 'call_date desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    # --- Customer / identity -------------------------------------------------
    channel_id = fields.Many2one('crm.channel', string='Channel', required=True, tracking=True,
                                  domain=[('code', '=', 'call')])
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True, index=True)
    partner_name = fields.Char(string='Customer Name (as received)')
    phone_number = fields.Char(string='Phone Number', required=True, index=True)
    lead_id = fields.Many2one('crm.lead', string='CRM Lead', tracking=True, index=True)
    external_call_id = fields.Char(string='External Call / CDR ID',
                                    help='Reference ID from the IP calling provider (e.g. Race Online).')

    # --- Routing / lifecycle ---------------------------------------------------
    direction = fields.Selection([
        ('inbound', 'Incoming'),
        ('outbound', 'Outgoing'),
    ], required=True, default='inbound', tracking=True)
    agent_id = fields.Many2one('res.users', string='Agent', tracking=True, index=True)
    team_id = fields.Many2one('crm.team', string='Sales Team',
                               default=lambda self: self.env['crm.team'].search(
                                   [('company_id', 'in', [self.env.company.id, False])], limit=1))
    state = fields.Selection([
        ('new', 'New'),
        ('ringing', 'Ringing'),
        ('answered', 'Answered'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('rejected', 'Rejected'),
    ], default='new', required=True, tracking=True, index=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], default='1', tracking=True)
    tag_ids = fields.Many2many('crm.communication.tag', string='Tags')
    is_conference = fields.Boolean(string='Conference Call')
    transferred_to_id = fields.Many2one('res.users', string='Transferred To')
    hold_count = fields.Integer(string='Times Put on Hold', default=0)

    # --- Timing ---------------------------------------------------------
    call_date = fields.Datetime(string='Call Started', default=fields.Datetime.now, required=True)
    answered_date = fields.Datetime(string='Answered At')
    end_date = fields.Datetime(string='Call Ended')
    duration_seconds = fields.Integer(string='Duration (s)', compute='_compute_duration', store=True)

    # --- After Call Work ---------------------------------------------------------
    disposition = fields.Selection([
        ('interested', 'Interested'),
        ('not_interested', 'Not Interested'),
        ('callback', 'Call Back Later'),
        ('wrong_number', 'Wrong Number'),
        ('no_answer', 'No Answer'),
        ('voicemail', 'Left Voicemail'),
        ('other', 'Other'),
    ], string='Disposition')
    agent_notes = fields.Text(string='Agent Notes')

    # --- Recording ---------------------------------------------------------
    recording_ids = fields.One2many('crm.call.recording', 'call_id', string='Recordings')
    recording_count = fields.Integer(compute='_compute_recording_count')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    # =====================================================================
    # COMPUTE
    # =====================================================================
    @api.depends('partner_id', 'partner_name', 'phone_number', 'direction')
    def _compute_display_name(self):
        for rec in self:
            name = rec.partner_id.name or rec.partner_name or rec.phone_number or _('Unknown Caller')
            arrow = '→' if rec.direction == 'outbound' else '←'
            rec.display_name = f'{name} {arrow}'

    @api.depends('answered_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.answered_date and rec.end_date:
                rec.duration_seconds = int((rec.end_date - rec.answered_date).total_seconds())
            else:
                rec.duration_seconds = 0

    def _compute_recording_count(self):
        for rec in self:
            rec.recording_count = len(rec.recording_ids)

    # =====================================================================
    # CRUD
    # =====================================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('channel_id'):
                call_channel = self.env['crm.channel'].search([('code', '=', 'call')], limit=1)
                if call_channel:
                    vals['channel_id'] = call_channel.id
        calls = super().create(vals_list)
        for call in calls:
            call._find_or_create_customer()
            if not call.agent_id:
                call._auto_assign_agent()
            call._find_or_create_lead()
            self.env['crm.communication'].sudo().create_from_call(call)
        return calls

    def write(self, vals):
        res = super().write(vals)
        sync_fields = {'state', 'priority', 'tag_ids', 'call_date', 'lead_id', 'agent_id'}
        if sync_fields.intersection(vals.keys()):
            for call in self:
                self.env['crm.communication'].sudo().create_from_call(call)
        return res

    # =====================================================================
    # CRM AUTOMATION
    # =====================================================================
    def _auto_assign_agent(self):
        """Consult crm.assignment.rule first (keyword / VIP / working-hours /
        department routing); fall back to plain round-robin if no rule matches."""
        for rec in self:
            agent, team = self.env['crm.assignment.rule'].sudo().resolve_agent(
                rec.channel_id, partner=rec.partner_id, message_body=None)
            if not agent:
                agent = self.env['crm.omni.utils'].assign_next_agent(
                    'crm_omnichannel_hub.last_assigned_agent_id_call')
            vals = {}
            if agent:
                vals['agent_id'] = agent.id
            if team and not rec.team_id:
                vals['team_id'] = team.id
            if vals:
                rec.sudo().write(vals)

    def _find_or_create_customer(self):
        Utils = self.env['crm.omni.utils']
        for rec in self:
            if rec.partner_id:
                continue
            partner = Utils.find_or_create_partner(
                name=rec.partner_name,
                phone=rec.phone_number,
                external_identifier=rec.phone_number,
                channel=rec.channel_id,
            )
            rec.sudo().write({'partner_id': partner.id})

    def _find_or_create_lead(self):
        Utils = self.env['crm.omni.utils']
        for rec in self:
            if rec.lead_id or not rec.partner_id:
                continue
            lead = Utils.find_or_create_lead(
                rec.partner_id, channel=rec.channel_id, agent=rec.agent_id,
                team=rec.team_id, priority=rec.priority)
            rec.sudo().write({'lead_id': lead.id})

    # =====================================================================
    # CALL LIFECYCLE ACTIONS
    # (Hooks for the IP Calling connector / click-to-call UI. Kept
    # self-contained here so the Call Center board is fully usable even
    # before a live telephony connector is installed.)
    # =====================================================================
    def action_answer(self):
        self.write({'state': 'answered', 'answered_date': fields.Datetime.now()})

    def action_reject(self):
        self.write({'state': 'rejected', 'end_date': fields.Datetime.now()})
        self._schedule_missed_call_followup()

    def action_hold(self):
        for rec in self:
            rec.write({'state': 'on_hold', 'hold_count': rec.hold_count + 1})

    def action_resume(self):
        self.write({'state': 'answered'})

    def action_transfer(self, user_id):
        self.write({'transferred_to_id': user_id, 'agent_id': user_id})
        self.message_post(body=_('Call transferred.'))

    def action_complete(self):
        for rec in self:
            vals = {'state': 'completed', 'end_date': fields.Datetime.now()}
            if not rec.answered_date:
                vals['answered_date'] = rec.call_date
            rec.write(vals)

    def action_mark_missed(self):
        self.write({'state': 'missed', 'end_date': fields.Datetime.now()})
        self._schedule_missed_call_followup()

    def _schedule_missed_call_followup(self):
        for rec in self:
            if not rec.agent_id:
                continue
            rec.activity_schedule(
                'mail.mail_activity_data_call',
                summary=_('Follow up on missed call'),
                note=_('Missed/rejected call from %(name)s.') % {
                    'name': rec.partner_id.name or rec.partner_name or rec.phone_number},
                user_id=rec.agent_id.id,
            )

    def action_view_lead(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': self.lead_id.id,
            'target': 'current',
        }

    @api.model
    def action_click_to_call(self, partner_id=None, phone_number=None):
        """Create an outbound call log entry. Intended to be called from a
        button on the partner/lead form (or by a future connector) to
        initiate a click-to-call. Actual dialing is performed by the
        IP Calling connector module once installed; this method only
        creates the CRM-side record and popup window data."""
        partner = self.env['res.partner'].browse(partner_id) if partner_id else self.env['res.partner']
        vals = {
            'direction': 'outbound',
            'partner_id': partner.id if partner else False,
            'partner_name': partner.name if partner else False,
            'phone_number': phone_number or partner.phone or partner.mobile,
            'agent_id': self.env.user.id,
            'state': 'ringing',
        }
        call = self.create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.call.log',
            'view_mode': 'form',
            'res_id': call.id,
            'target': 'new',
        }
