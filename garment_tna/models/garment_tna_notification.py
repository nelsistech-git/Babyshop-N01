# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentTnaNotification(models.Model):
    """Auto Escalation + Notification Channels (SRS sections 17-18) —
    garment.tna.notification."""
    _name = 'garment.tna.notification'
    _description = 'Garment TNA Notification'
    _order = 'create_date desc'

    tna_id = fields.Many2one('garment.tna', string='TNA', required=True, ondelete='cascade')
    # FIXED: Changed tna_id to parent.id in domain
    activity_id = fields.Many2one('garment.tna.activity', string='Related Activity',
                                   domain="[('tna_id', '=', parent.id)]")
    escalation_level = fields.Selection([
        ('1', 'Level 1: Responsible Person'), ('2', 'Level 2: Department Manager'),
        ('3', 'Level 3: General Manager'), ('4', 'Level 4: Managing Director'),
    ], string='Escalation Level', default='1')
    channel = fields.Selection([
        ('odoo', 'Odoo Notification'), ('email', 'Email'), ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'), ('push', 'Mobile Push Notification'),
    ], string='Channel', required=True, default='odoo')
    recipient_id = fields.Many2one('res.users', string='Recipient')
    subject = fields.Char(string='Subject', required=True)
    message = fields.Text(string='Message')
    sent_date = fields.Datetime(string='Sent Date')
    status = fields.Selection([
        ('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'),
    ], string='Status', default='pending')

    def action_mark_sent(self):
        self.write({'status': 'sent', 'sent_date': fields.Datetime.now()})