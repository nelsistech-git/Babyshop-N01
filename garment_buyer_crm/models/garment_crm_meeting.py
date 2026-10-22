# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentCRMMeeting(models.Model):
    """Buyer meeting management — SRS Buyer CRM section 16."""
    _name = 'garment.crm.meeting'
    _description = 'Garment Buyer Meeting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    meeting_number = fields.Char(string='Meeting Number', copy=False, readonly=True, default=lambda s: _('New'))
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True, ondelete='cascade')
    buyer_contact_ids = fields.Many2many('garment.buyer.contact', string='Buyer Participants',
                                          domain="[('buyer_id', '=', buyer_id)]")
    internal_participant_ids = fields.Many2many('res.users', string='Internal Participants')

    meeting_type = fields.Selection([
        ('initial_meeting', 'Initial Meeting'),
        ('buyer_visit', 'Buyer Visit'),
        ('product_presentation', 'Product Presentation'),
        ('costing_discussion', 'Costing Discussion'),
        ('sample_review', 'Sample Review'),
        ('negotiation', 'Negotiation'),
        ('compliance_audit', 'Compliance Audit'),
        ('quality_discussion', 'Quality Discussion'),
        ('shipment_planning', 'Shipment Planning'),
        ('annual_business_review', 'Annual Business Review'),
    ], string='Meeting Type', required=True, default='initial_meeting')

    venue = fields.Char(string='Venue')
    online_meeting_link = fields.Char(string='Online Meeting Link')
    date_start = fields.Datetime(string='Date & Time', default=fields.Datetime.now, required=True)
    duration = fields.Float(string='Duration (Hours)', default=1.0)
    date_end = fields.Datetime(string='End Time', compute='_compute_date_end', store=True)

    agenda = fields.Text(string='Agenda')
    discussion = fields.Text(string='Discussion')
    decisions = fields.Text(string='Decisions')
    action_items = fields.Text(string='Action Items')
    minutes_of_meeting = fields.Text(string='Minutes of Meeting (MoM)')
    follow_up_date = fields.Date(string='Follow-up Date')

    related_opportunity_id = fields.Many2one('garment.opportunity', string='Related Opportunity',
                                               domain="[('buyer_id', '=', buyer_id)]")
    organizer_id = fields.Many2one('res.users', string='Organizer', default=lambda s: s.env.user)
    state = fields.Selection([
        ('planned', 'Planned'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='planned', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    @api.depends('date_start', 'duration')
    def _compute_date_end(self):
        for rec in self:
            if rec.date_start:
                rec.date_end = fields.Datetime.add(rec.date_start, hours=rec.duration or 0.0)
            else:
                rec.date_end = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('meeting_number', _('New')) == _('New'):
                vals['meeting_number'] = self.env['ir.sequence'].next_by_code('garment.crm.meeting') or _('New')
        return super().create(vals_list)

    def action_mark_completed(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
