# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
PLM Notification System (SRS section 48) — garment.plm.notification.
Log of alerts raised against a PLM Project (approval pending, sample delay,
ECN required, buyer feedback, production handover).
"""
from odoo import fields, models


class GarmentPlmNotification(models.Model):
    _name = 'garment.plm.notification'
    _description = 'Garment PLM Notification'
    _order = 'create_date desc'

    project_id = fields.Many2one('garment.plm.project', string='PLM Project', required=True, ondelete='cascade')
    style_id = fields.Many2one(related='project_id.style_id', string='Style', store=True, readonly=True)

    notification_type = fields.Selection([
        ('approval_pending', 'Approval Pending'),
        ('sample_delay', 'Sample Delay'),
        ('stage_delay', 'Stage Delay'),
        ('ecn_required', 'ECN Required'),
        ('buyer_feedback', 'Buyer Feedback'),
        ('production_handover', 'Production Handover'),
    ], string='Type', required=True, default='approval_pending')

    recipient_id = fields.Many2one('res.users', string='Recipient')
    subject = fields.Char(string='Subject', required=True)
    message = fields.Text(string='Message')
    sent_date = fields.Datetime(string='Sent Date')
    status = fields.Selection([
        ('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'),
    ], string='Status', default='pending')

    def action_mark_sent(self):
        self.write({'status': 'sent', 'sent_date': fields.Datetime.now()})
