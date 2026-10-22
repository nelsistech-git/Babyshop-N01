# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentBuyerCommunication(models.Model):
    _name = 'garment.buyer.communication'
    _description = 'Garment Buyer Communication Log'
    _order = 'date desc'
    _inherit = ['mail.thread']

    comm_number = fields.Char(string='Communication Number', copy=False, readonly=True,
                               default=lambda s: _('New'))
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, ondelete='cascade')
    buyer_contact_id = fields.Many2one('garment.buyer.contact', string='Buyer Contact',
                                        domain="[('buyer_id', '=', buyer_id)]")
    date = fields.Datetime(string='Date & Time', default=fields.Datetime.now, required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda s: s.env.user)
    communication_type = fields.Selection([
        ('phone_call', 'Phone Call'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp Message'),
        ('meeting', 'Meeting'),
        ('zoom', 'Zoom Meeting'),
        ('teams', 'Microsoft Teams Meeting'),
        ('google_meet', 'Google Meet Session'),
        ('sms', 'SMS'),
        ('courier', 'Courier Dispatch'),
        ('document_sharing', 'Document Sharing'),
        ('factory_visit', 'Factory Visit'),
        ('buyer_audit', 'Buyer Audit'),
    ], string='Communication Type', required=True)
    subject = fields.Char(string='Subject', required=True)
    summary = fields.Text(string='Summary')
    follow_up_date = fields.Date(string='Follow-up Date')
    attachment = fields.Binary(string='Attachment', attachment=True)
    attachment_filename = fields.Char(string='Filename')
    outcome = fields.Selection([
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
        ('pending', 'Pending'),
    ], string='Outcome', default='pending')
    next_action = fields.Char(string='Next Action')
    related_opportunity_id = fields.Many2one('garment.opportunity', string='Related Opportunity',
                                              domain="[('buyer_id', '=', buyer_id)]")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('comm_number', _('New')) == _('New'):
                vals['comm_number'] = self.env['ir.sequence'].next_by_code('garment.buyer.communication') or _('New')
        return super().create(vals_list)
