# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentBuyerVisit(models.Model):
    """Buyer factory visit planning — SRS Buyer CRM section 18."""
    _name = 'garment.buyer.visit'
    _description = 'Garment Buyer Factory Visit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'arrival_date desc'

    visit_number = fields.Char(string='Visit Number', copy=False, readonly=True, default=lambda s: _('New'))
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True, ondelete='cascade')
    visitor_name = fields.Char(string='Visitor Name', required=True)
    visitor_company = fields.Char(string='Company')
    passport_number = fields.Char(string='Passport Number')
    nationality_id = fields.Many2one('res.country', string='Nationality')

    arrival_date = fields.Date(string='Arrival Date', tracking=True)
    departure_date = fields.Date(string='Departure Date')
    hotel_info = fields.Char(string='Hotel Information')
    airport_pickup = fields.Boolean(string='Airport Pickup')
    driver_name = fields.Char(string='Driver')
    vehicle = fields.Char(string='Vehicle')

    meeting_schedule = fields.Text(string='Meeting Schedule')
    factory_tour = fields.Boolean(string='Factory Tour')
    audit_schedule = fields.Text(string='Audit Schedule')
    lunch_dinner_arrangement = fields.Char(string='Lunch/Dinner Arrangement')
    feedback = fields.Text(string='Feedback')
    visit_outcome = fields.Selection([
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
        ('follow_up_required', 'Follow-up Required'),
    ], string='Visit Outcome')

    # Visit Checklist
    checklist_visitor_pass = fields.Boolean(string='Visitor Pass')
    checklist_nda_signed = fields.Boolean(string='NDA Signed')
    checklist_safety_briefing = fields.Boolean(string='Safety Briefing')
    checklist_ppe_issued = fields.Boolean(string='PPE Issued')
    checklist_meeting_room_reserved = fields.Boolean(string='Meeting Room Reserved')
    checklist_presentation_ready = fields.Boolean(string='Presentation Ready')
    checklist_product_samples_ready = fields.Boolean(string='Product Samples Ready')
    checklist_factory_cleanliness = fields.Boolean(string='Factory Cleanliness Confirmed')
    checklist_audit_documents_ready = fields.Boolean(string='Audit Documents Ready')
    checklist_progress = fields.Float(string='Checklist Completion (%)', compute='_compute_checklist_progress',
                                       store=True)

    host_user_id = fields.Many2one('res.users', string='Hosted By', default=lambda s: s.env.user)
    state = fields.Selection([
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='planned', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _checklist_fields = [
        'checklist_visitor_pass', 'checklist_nda_signed', 'checklist_safety_briefing',
        'checklist_ppe_issued', 'checklist_meeting_room_reserved', 'checklist_presentation_ready',
        'checklist_product_samples_ready', 'checklist_factory_cleanliness', 'checklist_audit_documents_ready',
    ]

    @api.depends(*_checklist_fields)
    def _compute_checklist_progress(self):
        total = len(self._checklist_fields)
        for rec in self:
            done = sum(1 for f in self._checklist_fields if rec[f])
            rec.checklist_progress = (done / total * 100.0) if total else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('visit_number', _('New')) == _('New'):
                vals['visit_number'] = self.env['ir.sequence'].next_by_code('garment.buyer.visit') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
