# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
BI Report Scheduler (SRS sections 20, 26-30, 52-54) — garment.report.schedule.

Defines WHAT report, HOW OFTEN and TO WHOM — the configuration surface the
SRS asks for. The actual rendering (PDF/Excel/CSV/PPTX generation) and
delivery (email/WhatsApp/mobile push) engine is NOT implemented here: it
would need a QWeb/Excel report template per report_category plus an outbound
mail/WhatsApp integration, both out of scope for a self-contained addon
module. See IMPLEMENTATION_NOTES.md — ``next_run_date`` is computed for
display only and nothing currently reads it to actually trigger a send.
"""
from odoo import api, fields, models

WEEKDAY_SELECTION = [
    ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'),
    ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday'),
]


class GarmentReportSchedule(models.Model):
    _name = 'garment.report.schedule'
    _description = 'Garment BI Report Schedule'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Report Name', required=True, tracking=True)
    report_category = fields.Selection([
        ('executive', 'Executive'), ('production', 'Production'), ('quality', 'Quality'),
        ('inventory', 'Inventory'), ('finance', 'Finance'), ('hr', 'HR'),
        ('buyer', 'Buyer Analytics'), ('supplier', 'Supplier Analytics'),
    ], string='Report Category', required=True, default='executive')
    board_id = fields.Many2one('garment.dashboard.board', string='Source Dashboard',
                                help='Optional dashboard this report is built from.')
    kpi_ids = fields.Many2many('garment.kpi.definition', string='Included KPIs')

    frequency = fields.Selection([
        ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('yearly', 'Yearly'),
    ], string='Frequency', required=True, default='daily', tracking=True)
    send_time = fields.Float(string='Send Time (24h)', default=8.0,
                              help='Hour of day to send, e.g. 8.0 = 08:00, 17.5 = 17:30.')
    weekday = fields.Selection(WEEKDAY_SELECTION, string='Day Of Week', default='0',
                                help='Used when Frequency = Weekly.')
    day_of_month = fields.Integer(string='Day Of Month', default=1,
                                   help='Used when Frequency = Monthly or Yearly (1-28).')

    format = fields.Selection([
        ('pdf', 'PDF'), ('excel', 'Excel'), ('csv', 'CSV'), ('pptx', 'PowerPoint'),
    ], string='Export Format', required=True, default='pdf')

    delivery_email = fields.Boolean(string='Email', default=True)
    delivery_whatsapp = fields.Boolean(string='WhatsApp', default=False)
    delivery_mobile_push = fields.Boolean(string='Mobile Notification', default=False)
    recipient_user_ids = fields.Many2many('res.users', string='Recipient Users')
    recipient_emails = fields.Char(string='Additional Recipient Emails',
                                    help='Comma-separated external email addresses.')

    next_run_date = fields.Date(string='Next Run (indicative)', compute='_compute_next_run_date', store=True)
    last_sent_date = fields.Datetime(string='Last Sent', readonly=True, copy=False)

    state = fields.Selection([
        ('active', 'Active'), ('paused', 'Paused'),
    ], string='Status', default='active', tracking=True)
    active = fields.Boolean(default=True)
    notes = fields.Text(
        string='Notes',
        default='Report rendering and email/WhatsApp/mobile delivery are not implemented in this '
                'module — this record only captures the schedule configuration. See '
                'IMPLEMENTATION_NOTES.md.')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('frequency', 'weekday', 'day_of_month', 'send_time', 'state')
    def _compute_next_run_date(self):
        """Indicative next-run date only, for the list/form UI — no cron reads this
        field to actually trigger anything (see module docstring above)."""
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state != 'active':
                rec.next_run_date = False
                continue
            if rec.frequency == 'daily':
                rec.next_run_date = today
            elif rec.frequency == 'weekly':
                target_weekday = int(rec.weekday or '0')
                delta = (target_weekday - today.weekday()) % 7
                rec.next_run_date = fields.Date.add(today, days=delta)
            elif rec.frequency in ('monthly', 'yearly'):
                day = max(1, min(rec.day_of_month or 1, 28))
                candidate = today.replace(day=day)
                if candidate < today:
                    candidate = fields.Date.add(candidate, months=1) if rec.frequency == 'monthly' \
                        else candidate.replace(year=candidate.year + 1)
                rec.next_run_date = candidate
            else:
                rec.next_run_date = False

    def action_activate(self):
        self.write({'state': 'active'})

    def action_pause(self):
        self.write({'state': 'paused'})
