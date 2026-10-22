# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentCRMActivity(models.Model):
    """Buyer Activity Scheduler — SRS Buyer CRM section 15.

    This is intentionally a dedicated, lightweight model rather than a
    subclass of ``mail.activity``: the SRS asks for domain-specific fields
    (Activity Number, a garment-specific type list including Zoom/Google
    Meet/Quotation & Payment reminders, structured Reminder Options and
    Completion Notes) that don't map cleanly onto Odoo's generic activity
    mixin, which ``garment.buyer`` / ``garment.opportunity`` / ``garment.rfq``
    already inherit for their own chatter-driven to-dos.
    """
    _name = 'garment.crm.activity'
    _description = 'Garment Buyer Activity (Scheduler)'
    _inherit = ['mail.thread']
    _order = 'start_date'

    activity_number = fields.Char(string='Activity Number', copy=False, readonly=True, default=lambda s: _('New'))
    subject = fields.Char(string='Subject', required=True)
    description = fields.Text(string='Description')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', tracking=True, ondelete='cascade')
    related_opportunity_id = fields.Many2one('garment.opportunity', string='Related Opportunity',
                                               domain="[('buyer_id', '=', buyer_id)]")
    assigned_user_id = fields.Many2one('res.users', string='Assigned User', default=lambda s: s.env.user,
                                        tracking=True)

    activity_type = fields.Selection([
        ('phone_call', 'Phone Call'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('zoom_meeting', 'Zoom Meeting'),
        ('google_meet', 'Google Meet'),
        ('factory_visit', 'Factory Visit'),
        ('buyer_visit', 'Buyer Visit'),
        ('follow_up', 'Follow-up'),
        ('quotation_reminder', 'Quotation Reminder'),
        ('payment_reminder', 'Payment Reminder'),
        ('shipment_update', 'Shipment Update'),
        ('complaint_resolution', 'Complaint Resolution'),
    ], string='Activity Type', required=True, default='follow_up')

    start_date = fields.Datetime(string='Start Date', default=fields.Datetime.now, required=True)
    end_date = fields.Datetime(string='End Date')
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Very High'),
    ], string='Priority', default='1')
    status = fields.Selection([
        ('planned', 'Planned'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('overdue', 'Overdue'),
    ], string='Status', default='planned', tracking=True, group_expand='_expand_states')

    reminder = fields.Selection([
        ('10_min', '10 Minutes Before'),
        ('30_min', '30 Minutes Before'),
        ('1_hour', '1 Hour Before'),
        ('1_day', '1 Day Before'),
        ('3_days', '3 Days Before'),
        ('1_week', '1 Week Before'),
        ('custom', 'Custom Reminder'),
    ], string='Reminder')
    reminder_custom_minutes = fields.Integer(string='Custom Reminder (minutes before)')
    completion_notes = fields.Text(string='Completion Notes')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('activity_number', _('New')) == _('New'):
                vals['activity_number'] = self.env['ir.sequence'].next_by_code('garment.crm.activity') or _('New')
        return super().create(vals_list)

    def action_start(self):
        self.write({'status': 'in_progress'})

    def action_complete(self):
        self.write({'status': 'completed'})

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    @api.model
    def _cron_mark_overdue_activities(self):
        """Scheduled action (Automation Rules, section 40: 'Escalate overdue
        activities') — flags activities whose end date has passed and are
        still open."""
        now = fields.Datetime.now()
        overdue = self.search([
            ('end_date', '<', now),
            ('status', 'not in', ['completed', 'cancelled', 'overdue']),
        ])
        overdue.write({'status': 'overdue'})
        for activity in overdue:
            if activity.assigned_user_id:
                activity.message_post(
                    body=_('Activity "%s" is overdue.') % activity.subject,
                    partner_ids=activity.assigned_user_id.partner_id.ids,
                )
