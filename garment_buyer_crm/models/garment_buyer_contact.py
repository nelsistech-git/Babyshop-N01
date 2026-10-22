# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentBuyerContact(models.Model):
    _name = 'garment.buyer.contact'
    _description = 'Garment Buyer Contact Person'
    _order = 'sequence, name'

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Contact Name', required=True)
    designation = fields.Char(string='Designation')
    department = fields.Char(string='Department')
    email = fields.Char(string='Email')
    mobile = fields.Char(string='Mobile')
    whatsapp = fields.Char(string='WhatsApp')
    extension = fields.Char(string='Extension')
    linkedin = fields.Char(string='LinkedIn')
    birthday = fields.Date(string='Birthday')
    anniversary = fields.Date(string='Anniversary')
    is_decision_maker = fields.Boolean(string='Decision Maker')
    is_influencer = fields.Boolean(string='Influencer')
    is_technical_contact = fields.Boolean(string='Technical Contact')
    is_finance_contact = fields.Boolean(string='Finance Contact')
    is_shipment_contact = fields.Boolean(string='Shipment Contact')
    is_sample_contact = fields.Boolean(string='Sample Contact')
    notes = fields.Text(string='Notes')

    @api.model
    def _cron_notify_birthdays(self):
        """Automation Rules (SRS section 40): 'Trigger birthday and
        anniversary greetings'."""
        today = fields.Date.context_today(self)
        contacts = self.search([])
        for contact in contacts:
            for date_field, label in (('birthday', _('Birthday')), ('anniversary', _('Anniversary'))):
                value = contact[date_field]
                if value and value.month == today.month and value.day == today.day:
                    contact.buyer_id.message_post(
                        body=_('%s: today is %s\'s %s.') % (label, contact.name, label.lower())
                    )
