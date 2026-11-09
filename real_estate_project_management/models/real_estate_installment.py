# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api


class RealEstateInstallment(models.Model):
    """A single scheduled payment (equal installment or milestone line)
    within an Installment Plan. Status is recomputed daily by a cron
    (see ir.cron in data/) since it depends on 'today', which can't be
    expressed as an ORM @api.depends trigger."""
    _name = 'real.estate.installment'
    _description = 'Real Estate Installment'
    _inherit = ['mail.thread']
    _rec_name = 'display_name'
    _order = 'plan_id, installment_number, due_date'

    plan_id = fields.Many2one('real.estate.installment.plan', string='Installment Plan',
                               required=True, ondelete='cascade')
    customer_id = fields.Many2one(related='plan_id.customer_id', store=True, readonly=True)
    project_id = fields.Many2one(related='plan_id.project_id', store=True, readonly=True)
    unit_id = fields.Many2one(related='plan_id.unit_id', store=True, readonly=True)

    installment_number = fields.Integer(string='#')
    milestone_name = fields.Char(string='Milestone', help='e.g. "Foundation Complete" - used '
                                                            'for milestone-based plans.')
    milestone_percentage = fields.Float(string='Milestone %', digits=(5, 2))
    milestone_triggered = fields.Boolean(string='Milestone Achieved', default=False)
    display_name = fields.Char(compute='_compute_display_name', store=True)

    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    amount = fields.Monetary(string='Amount', required=True)

    collection_ids = fields.One2many('real.estate.collection', 'installment_id', string='Collections')
    paid_amount = fields.Monetary(string='Paid Amount', compute='_compute_paid_amount', store=True)
    due_amount = fields.Monetary(string='Outstanding', compute='_compute_paid_amount', store=True)

    grace_period_days = fields.Integer(related='plan_id.grace_period_days', readonly=True)
    late_fee_amount = fields.Monetary(string='Late Fee', compute='_compute_late_fee', store=True)

    status = fields.Selection([
        ('upcoming', 'Upcoming'),
        ('due_today', 'Due Today'),
        ('overdue', 'Overdue'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='upcoming', required=True, tracking=True)

    company_id = fields.Many2one(related='plan_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='plan_id.currency_id', readonly=True)

    @api.depends('plan_id.name', 'installment_number', 'milestone_name')
    def _compute_display_name(self):
        for rec in self:
            base = rec.plan_id.name or ''
            if rec.milestone_name:
                rec.display_name = '%s - %s' % (base, rec.milestone_name)
            else:
                rec.display_name = '%s - Installment %s' % (base, rec.installment_number or '?')

    @api.depends('collection_ids.amount', 'collection_ids.state', 'amount')
    def _compute_paid_amount(self):
        for rec in self:
            paid = sum(rec.collection_ids.filtered(lambda c: c.state == 'confirmed').mapped('amount'))
            rec.paid_amount = paid
            rec.due_amount = rec.amount - paid

    @api.depends('due_date', 'due_amount', 'status', 'plan_id.late_fee_type', 'plan_id.late_fee_value',
                 'plan_id.grace_period_days')
    def _compute_late_fee(self):
        today = fields.Date.context_today(self)
        for rec in self:
            plan = rec.plan_id
            if not plan or plan.late_fee_type == 'none' or rec.due_amount <= 0 or not rec.due_date:
                rec.late_fee_amount = 0.0
                continue
            grace_end = rec.due_date + timedelta(days=plan.grace_period_days or 0)
            if today <= grace_end:
                rec.late_fee_amount = 0.0
                continue
            overdue_days = (today - grace_end).days
            if plan.late_fee_type == 'fixed':
                rec.late_fee_amount = plan.late_fee_value
            elif plan.late_fee_type == 'percentage':
                rec.late_fee_amount = rec.amount * (plan.late_fee_value or 0.0) / 100.0
            elif plan.late_fee_type == 'monthly_penalty':
                months_overdue = max(1, (overdue_days // 30) + 1)
                rec.late_fee_amount = rec.amount * (plan.late_fee_value or 0.0) / 100.0 * months_overdue
            else:
                rec.late_fee_amount = 0.0

    def _compute_status_now(self):
        """Recompute status for these records based on today's date and
        current paid_amount. Called by the daily cron and by manual
        'Recompute Statuses' buttons."""
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.plan_id.state == 'cancelled':
                new_status = 'cancelled'
            elif rec.due_amount <= 0:
                new_status = 'paid'
            elif rec.paid_amount > 0:
                new_status = 'partially_paid'
            elif rec.due_date and rec.due_date < today:
                new_status = 'overdue'
            elif rec.due_date == today:
                new_status = 'due_today'
            else:
                new_status = 'upcoming'
            if new_status != rec.status:
                rec.status = new_status

    def action_trigger_milestone(self):
        """Mark a milestone as achieved - the corresponding installment
        becomes due immediately, per spec section 38."""
        for rec in self:
            rec.write({
                'milestone_triggered': True,
                'due_date': fields.Date.context_today(rec),
            })
        self._compute_status_now()

    def action_send_reminder(self):
        """Integration hook for Email/SMS/WhatsApp reminders (spec
        section 41/67). No provider credentials are hardcoded here -
        this posts a chatter log entry; wiring an actual provider is a
        configuration-time integration, not application logic."""
        for rec in self:
            rec.message_post(body='Payment reminder logged for %s (due %s, outstanding %.2f).' % (
                rec.display_name, rec.due_date, rec.due_amount))

    @api.model
    def cron_update_all_statuses(self):
        """Scheduled action (see data/ir_cron_data.xml): find overdue
        installments and refresh every non-final status daily."""
        installments = self.search([('status', 'not in', ('paid', 'cancelled'))])
        installments._compute_status_now()
