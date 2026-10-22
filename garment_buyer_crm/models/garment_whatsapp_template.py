# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentWhatsAppTemplate(models.Model):
    """Configurable WhatsApp message template master — SRS Buyer CRM section
    25 (WhatsApp Integration / WhatsApp Automation) and section 29 menu
    ("Configuration > WhatsApp Templates").

    This module stores the template content and maps it to the automation
    event it fires on; actually dispatching messages through the WhatsApp
    Business API is an outbound integration concern left to the
    infrastructure layer (see IMPLEMENTATION_NOTES.md) so this module
    always installs cleanly with zero external credentials configured.
    """
    _name = 'garment.whatsapp.template'
    _description = 'Garment Buyer WhatsApp Message Template'
    _order = 'sequence, name'

    name = fields.Char(string='Template Name', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    trigger_event = fields.Selection([
        ('rfq_received', 'RFQ Received'),
        ('quotation_ready', 'Quotation Ready'),
        ('sample_shipped', 'Sample Shipped'),
        ('production_started', 'Production Started'),
        ('production_completed', 'Production Completed'),
        ('shipment_booked', 'Shipment Booked'),
        ('invoice_generated', 'Invoice Generated'),
        ('payment_due', 'Payment Due'),
        ('birthday_greeting', 'Birthday Greeting'),
        ('holiday_greeting', 'Holiday Greeting'),
        ('manual', 'Manual / Other'),
    ], string='Automation Trigger', default='manual', required=True)
    message_body = fields.Text(string='Message Body', required=True,
                                help='Supports simple ${object.field} style placeholders, resolved by the '
                                     'WhatsApp Business API integration layer at send time.')
    supports_media = fields.Boolean(string='Supports Media Attachment (image/doc/PDF/voice/video)', default=True)
