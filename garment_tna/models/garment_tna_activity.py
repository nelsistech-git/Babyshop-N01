# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class GarmentTnaActivity(models.Model):
    """TNA Activity Management (SRS sections 9-13) — garment.tna.activity."""
    _name = 'garment.tna.activity'
    _description = 'Garment TNA Activity'
    _inherit = ['mail.thread']
    _order = 'sequence, planned_end_date'

    tna_id = fields.Many2one('garment.tna', string='TNA', required=True, ondelete='cascade')
    # Denormalized/related for Calendar Filters and department dashboards
    # (SRS sections 21-22): filter/group activities by Buyer or Style
    # without leaving this model.
    buyer_id = fields.Many2one('garment.buyer', related='tna_id.buyer_id', string='Buyer', store=True)
    style_id = fields.Many2one('garment.style', related='tna_id.style_id', string='Style', store=True)
    sequence = fields.Integer(default=10)
    activity_code = fields.Char(string='Activity Code')
    activity_name = fields.Char(string='Activity Name', required=True, tracking=True)
    category = fields.Selection([
        ('merchandising', 'Merchandising'), ('product_development', 'Product Development'),
        ('material', 'Material'), ('production', 'Production'), ('quality', 'Quality'), ('commercial', 'Commercial'),
    ], string='Category', required=True)
    department = fields.Char(string='Department')
    responsible_person_id = fields.Many2one('res.users', string='Responsible Person', tracking=True)

    planned_start_date = fields.Date(string='Planned Start Date', tracking=True)
    planned_end_date = fields.Date(string='Planned End Date', required=True, tracking=True)
    actual_start_date = fields.Date(string='Actual Start Date', tracking=True)
    actual_end_date = fields.Date(string='Actual End Date', tracking=True)
    duration_days = fields.Integer(string='Duration (days)', compute='_compute_duration', store=True)

    dependency_type = fields.Selection([
        ('finish_to_start', 'Finish-to-Start'), ('start_to_start', 'Start-to-Start'),
        ('finish_to_finish', 'Finish-to-Finish'),
    ], string='Dependency Type')
    # FIXED: Changed tna_id to parent.id in domain
    predecessor_activity_id = fields.Many2one('garment.tna.activity', string='Predecessor Activity',
                                               domain="[('tna_id', '=', parent.id)]")

    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1')
    status = fields.Selection([
        ('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed'),
        ('delayed', 'Delayed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', tracking=True)
    progress_pct = fields.Float(string='Progress %', default=0.0)
    is_milestone = fields.Boolean(string='Milestone')
    is_critical_path = fields.Boolean(string='Critical Path', compute='_compute_critical_path', store=True)
    # Gantt Color Indicators (SRS section 20)
    delay_status = fields.Selection([
        ('normal', 'Normal'), ('warning', 'Warning'), ('delayed', 'Delayed'), ('critical', 'Critical'),
    ], string='Gantt Status', compute='_compute_delay_status', store=True)
    remarks = fields.Text(string='Remarks')

    @api.depends('planned_start_date', 'planned_end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.planned_start_date and rec.planned_end_date:
                rec.duration_days = (rec.planned_end_date - rec.planned_start_date).days
            else:
                rec.duration_days = 0

    @api.depends('status', 'is_milestone', 'predecessor_activity_id')
    def _compute_critical_path(self):
        """Critical Path Rules (SRS section 12)"""
        for rec in self:
            rec.is_critical_path = bool(
                rec.is_milestone
                or rec.status == 'delayed'
                or (rec.predecessor_activity_id and rec.predecessor_activity_id.status not in ('completed',))
            )

    @api.depends('status', 'planned_end_date', 'is_critical_path')
    def _compute_delay_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.status == 'completed':
                rec.delay_status = 'normal'
            elif rec.status == 'delayed' or (rec.planned_end_date and rec.planned_end_date < today):
                rec.delay_status = 'critical' if rec.is_critical_path else 'delayed'
            elif rec.planned_end_date and 0 <= (rec.planned_end_date - today).days <= 3:
                rec.delay_status = 'warning'
            else:
                rec.delay_status = 'normal'

    def write(self, vals):
        # Activity Dependency Automation (SRS section 26)
        if not self.env.context.get('tna_skip_dependency_check') and (
                'status' in vals or 'actual_start_date' in vals or 'actual_end_date' in vals):
            for rec in self:
                pred = rec.predecessor_activity_id
                dep_type = rec.dependency_type
                if not pred or not dep_type:
                    continue
                new_status = vals.get('status', rec.status)
                if dep_type == 'finish_to_start' and new_status in ('in_progress', 'completed') \
                        and pred.status != 'completed':
                    raise ValidationError(_(
                        '"%s" is Finish-to-Start dependent on "%s", which is not Completed yet.')
                        % (rec.activity_name, pred.activity_name))
                if dep_type == 'start_to_start' and new_status == 'in_progress' \
                        and pred.status == 'pending' and not pred.actual_start_date:
                    raise ValidationError(_(
                        '"%s" is Start-to-Start dependent on "%s", which has not started yet.')
                        % (rec.activity_name, pred.activity_name))
                if dep_type == 'finish_to_finish' and new_status == 'completed' and pred.status != 'completed':
                    raise ValidationError(_(
                        '"%s" is Finish-to-Finish dependent on "%s", which is not Completed yet.')
                        % (rec.activity_name, pred.activity_name))
        return super().write(vals)

    def action_mark_completed(self):
        self.write({'status': 'completed', 'progress_pct': 100.0, 'actual_end_date': fields.Date.context_today(self)})

    def action_mark_delayed(self):
        self.write({'status': 'delayed'})

    def _create_notification(self, channel, level, subject, message, recipient=None):
        self.ensure_one()
        recipient = recipient or self.responsible_person_id or self.tna_id.merchandiser_id or self.tna_id.owner_id
        notif = self.env['garment.tna.notification'].create({
            'tna_id': self.tna_id.id,
            'activity_id': self.id,
            'escalation_level': level,
            'channel': channel,
            'recipient_id': recipient.id if recipient else False,
            'subject': subject,
            'message': message,
        })
        if recipient and recipient.partner_id:
            self.tna_id.message_post(body=message, partner_ids=recipient.partner_id.ids)
        else:
            self.tna_id.message_post(body=message)
        notif.action_mark_sent()
        return notif

    @api.model
    def _cron_send_pre_due_reminders(self):
        today = fields.Date.context_today(self)
        open_states = ('pending', 'in_progress')
        for days in (7, 3, 1):
            due = today + timedelta(days=days)
            activities = self.search([('planned_end_date', '=', due), ('status', 'in', open_states)])
            for act in activities:
                act._create_notification(
                    channel='odoo', level='1',
                    subject=_('%s due in %d day(s)') % (act.activity_name, days),
                    message=_('Activity "%s" on TNA %s is due on %s (%d day(s) remaining).') % (
                        act.activity_name, act.tna_id.tna_number, act.planned_end_date, days))

    @api.model
    def _cron_send_overdue_reminders(self):
        today = fields.Date.context_today(self)
        overdue = self.search([
            ('planned_end_date', '<', today), ('status', 'in', ('pending', 'in_progress', 'delayed')),
        ])
        for act in overdue:
            act._create_notification(
                channel='odoo', level='1',
                subject=_('OVERDUE: %s') % act.activity_name,
                message=_('Activity "%s" on TNA %s was due on %s and is still open.') % (
                    act.activity_name, act.tna_id.tna_number, act.planned_end_date))

    @api.model
    def _cron_auto_escalate(self):
        today = fields.Date.context_today(self)
        overdue = self.search([
            ('planned_end_date', '<', today), ('status', 'in', ('pending', 'in_progress', 'delayed')),
        ])
        for act in overdue:
            days_overdue = (today - act.planned_end_date).days
            if days_overdue >= 15:
                level = '4'
            elif days_overdue >= 7:
                level = '3'
            elif days_overdue >= 3:
                level = '2'
            else:
                level = '1'
            already_today = self.env['garment.tna.notification'].search_count([
                ('activity_id', '=', act.id), ('escalation_level', '=', level),
                ('create_date', '>=', fields.Datetime.to_string(today)),
            ])
            if already_today:
                continue
            recipient = act.responsible_person_id
            if level in ('2', '3', '4'):
                recipient = act.tna_id.merchandiser_id or act.tna_id.owner_id
            act._create_notification(
                channel='odoo', level=level,
                subject=_('[Escalation L%s] %s overdue by %d day(s)') % (level, act.activity_name, days_overdue),
                message=_('Activity "%s" on TNA %s is %d day(s) overdue.') % (
                    act.activity_name, act.tna_id.tna_number, days_overdue),
                recipient=recipient)