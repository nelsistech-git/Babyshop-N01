# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentMerchCalendarEvent(models.Model):
    """Merchandising Calendar (SRS section 12) — garment.merch.calendar.event."""
    _name = 'garment.merch.calendar.event'
    _description = 'Garment Merchandising Calendar Event'
    _order = 'event_date'

    name = fields.Char(string='Title', required=True)
    event_type = fields.Selection([
        ('rfq_deadline', 'RFQ Deadline'), ('costing_deadline', 'Costing Deadline'),
        ('sample_deadline', 'Sample Deadline'), ('buyer_meeting', 'Buyer Meeting'),
        ('fabric_booking', 'Fabric Booking Date'), ('accessories_booking', 'Accessories Booking Date'),
        ('production_start', 'Production Start'), ('inspection', 'Inspection Date'),
        ('shipment', 'Shipment Date'), ('lc_deadline', 'LC Deadline'),
    ], string='Event Type', required=True)
    event_date = fields.Date(string='Date', required=True)
    inquiry_id = fields.Many2one('garment.merch.inquiry', string='Inquiry')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer')
    style_id = fields.Many2one('garment.style', string='Style')
    responsible_id = fields.Many2one('res.users', string='Responsible')
    is_completed = fields.Boolean(string='Completed')
    notes = fields.Text(string='Notes')

    def action_mark_completed(self):
        self.write({'is_completed': True})
