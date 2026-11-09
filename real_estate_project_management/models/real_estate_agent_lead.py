# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

AGENT_GROUP = 'real_estate_project_management.group_real_estate_agent'
MANAGER_GROUP = 'real_estate_project_management.group_real_estate_sales_manager'


class RealEstateAgentLead(models.Model):
    """Lightweight CRM for agents: prospects and existing customers with a
    pipeline stage, follow-up date, activity log and chatter. An agent sees
    and edits ONLY his own records (record rule on agent_id)."""
    _name = 'real.estate.agent.lead'
    _description = 'Agent CRM Lead / Customer Follow-up'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, next_followup_date, id desc'

    def _default_agent(self):
        partner = self.env.user.partner_id
        return partner if partner.is_agent else False

    name = fields.Char(string='Opportunity', required=True, tracking=True)
    agent_id = fields.Many2one('res.partner', string='Agent', required=True, index=True,
                                tracking=True, default=_default_agent,
                                domain="[('is_agent', '=', True)]", ondelete='restrict')
    is_agent_user = fields.Boolean(compute='_compute_is_agent_user')

    contact_name = fields.Char(string='Contact Name', tracking=True)
    phone = fields.Char(string='Phone / WhatsApp')
    email = fields.Char(string='Email')
    partner_id = fields.Many2one('res.partner', string='Existing Customer', ondelete='set null',
                                  help='Link an existing customer, or use "Convert to Customer".')

    project_id = fields.Many2one('real.estate.project', string='Interested Project', ondelete='set null')
    unit_id = fields.Many2one('real.estate.unit', string='Interested Unit', ondelete='set null',
                               domain="[('project_id', '=', project_id)]")
    expected_value = fields.Monetary(string='Expected Deal Value')
    source = fields.Selection([
        ('referral', 'Referral'),
        ('walk_in', 'Walk-in'),
        ('phone', 'Phone Call'),
        ('facebook', 'Facebook / Social'),
        ('website', 'Website'),
        ('event', 'Event / Fair'),
        ('other', 'Other'),
    ], string='Source', default='referral')

    stage = fields.Selection([
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('site_visit', 'Site Visit'),
        ('negotiation', 'Negotiation'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ], string='Stage', default='new', required=True, tracking=True, group_expand=True, index=True)
    priority = fields.Selection([('0', 'Normal'), ('1', 'Medium'), ('2', 'High'), ('3', 'Very High')],
                                 string='Priority', default='0')
    next_followup_date = fields.Date(string='Next Follow-up', tracking=True)
    last_contact_date = fields.Date(string='Last Contact')
    is_overdue = fields.Boolean(compute='_compute_is_overdue')
    lost_reason = fields.Char(string='Lost Reason')
    notes = fields.Html(string='Notes')
    color = fields.Integer(string='Color')

    log_ids = fields.One2many('real.estate.agent.lead.log', 'lead_id', string='Interaction Log')
    log_count = fields.Integer(compute='_compute_log_count')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.depends_context('uid')
    def _compute_is_agent_user(self):
        user = self.env.user
        flag = user.has_group(AGENT_GROUP) and not user.has_group(MANAGER_GROUP)
        for rec in self:
            rec.is_agent_user = flag

    @api.depends('next_followup_date', 'stage')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(
                rec.next_followup_date and rec.next_followup_date < today
                and rec.stage not in ('won', 'lost'))

    @api.depends('log_ids')
    def _compute_log_count(self):
        for rec in self:
            rec.log_count = len(rec.log_ids)

    # An agent can never hand his records to another agent.
    @api.model_create_multi
    def create(self, vals_list):
        user = self.env.user
        if user.has_group(AGENT_GROUP) and not user.has_group(MANAGER_GROUP):
            for vals in vals_list:
                vals['agent_id'] = user.partner_id.id
        return super().create(vals_list)

    def write(self, vals):
        user = self.env.user
        if 'agent_id' in vals and user.has_group(AGENT_GROUP) and not user.has_group(MANAGER_GROUP):
            vals = dict(vals, agent_id=user.partner_id.id)
        return super().write(vals)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.contact_name = self.contact_name or self.partner_id.name
            self.phone = self.phone or self.partner_id.mobile or self.partner_id.phone
            self.email = self.email or self.partner_id.email
            if not self.name:
                self.name = self.partner_id.name

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.unit_id and self.unit_id.project_id != self.project_id:
            self.unit_id = False

    # ---- stage buttons -------------------------------------------------
    def action_set_contacted(self):
        self.write({'stage': 'contacted', 'last_contact_date': fields.Date.context_today(self)})

    def action_set_site_visit(self):
        self.write({'stage': 'site_visit'})

    def action_set_negotiation(self):
        self.write({'stage': 'negotiation'})

    def action_set_won(self):
        self.write({'stage': 'won', 'next_followup_date': False})

    def action_set_lost(self):
        self.write({'stage': 'lost', 'next_followup_date': False})

    def action_reopen(self):
        self.write({'stage': 'new'})

    def action_convert_to_customer(self):
        """Create (or adopt) the customer record and tie it to this agent as
        the referrer - the first link of the commission chain. Done with
        sudo because agents cannot create contacts directly."""
        Partner = self.env['res.partner'].sudo()
        for rec in self:
            if rec.partner_id:
                if not rec.partner_id.referred_by_id and rec.partner_id != rec.agent_id:
                    rec.partner_id.sudo().write({'referred_by_id': rec.agent_id.id})
                continue
            name = rec.contact_name or rec.name
            if not name:
                raise UserError(_('Enter a contact name first.'))
            partner = Partner.create({
                'name': name,
                'phone': rec.phone,
                'email': rec.email,
                'customer_type': 'individual',
                'referred_by_id': rec.agent_id.id,
            })
            rec.partner_id = partner
            rec.message_post(body=_('Converted to customer: %s', partner.display_name))

    def action_create_booking(self):
        """Staff shortcut (sales team only): start a booking for this lead."""
        self.ensure_one()
        if not self.partner_id:
            self.action_convert_to_customer()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Booking'),
            'res_model': 'real.estate.booking',
            'view_mode': 'form',
            'context': {
                'default_customer_id': self.partner_id.id,
                'default_unit_id': self.unit_id.id,
                'default_agent_id': self.agent_id.id,
            },
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Interaction Log'),
            'res_model': 'real.estate.agent.lead.log',
            'view_mode': 'tree,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }
