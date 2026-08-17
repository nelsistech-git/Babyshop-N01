# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class RealEstateInstallmentPlan(models.Model):
    """The payment schedule for a Sale Agreement. Reads its financial
    inputs (net price, down payment, booking amount, frequency) off the
    Sale Agreement rather than duplicating them (per Phase 5's design),
    and generates either an equal-installment schedule or a manually
    curated milestone-based schedule."""
    _name = 'real.estate.installment.plan'
    _description = 'Real Estate Installment Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Plan Number', copy=False, tracking=True,
                        default='New', readonly=True)
    sale_agreement_id = fields.Many2one('real.estate.sale.agreement', string='Sale Agreement',
                                         required=True, tracking=True, ondelete='restrict')
    customer_id = fields.Many2one(related='sale_agreement_id.customer_id', store=True, readonly=True)
    unit_id = fields.Many2one(related='sale_agreement_id.unit_id', store=True, readonly=True)
    project_id = fields.Many2one(related='sale_agreement_id.project_id', store=True, readonly=True)

    total_amount = fields.Monetary(related='sale_agreement_id.net_price', string='Agreement Net Price',
                                    store=True, readonly=True)
    down_payment = fields.Monetary(related='sale_agreement_id.down_payment', store=True, readonly=True)
    booking_amount = fields.Monetary(related='sale_agreement_id.booking_amount', store=True, readonly=True)
    financeable_amount = fields.Monetary(string='Amount to Schedule', compute='_compute_financeable_amount',
                                          store=True,
                                          help='Net Price minus Down Payment and Booking Amount - '
                                               'this is the amount the installment lines must total.')

    plan_type = fields.Selection([
        ('equal', 'Equal Installments'),
        ('milestone', 'Milestone Based'),
    ], string='Plan Type', default='equal', required=True, tracking=True)
    frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half-Yearly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ], string='Frequency', default='monthly')
    custom_interval_days = fields.Integer(string='Custom Interval (Days)',
                                           help='Used only when Frequency = Custom.')
    number_of_installments = fields.Integer(string='Number of Installments')
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)

    grace_period_days = fields.Integer(string='Grace Period (Days)', default=0)
    late_fee_type = fields.Selection([
        ('none', 'None'),
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Installment'),
        ('monthly_penalty', 'Monthly Penalty (Compounding by Month Overdue)'),
    ], string='Late Fee Rule', default='none')
    late_fee_value = fields.Float(string='Late Fee Value',
                                   help='Fixed amount, or percentage (e.g. 2 = 2%) per the Late Fee Rule.')

    installment_ids = fields.One2many('real.estate.installment', 'plan_id', string='Installments')
    total_scheduled = fields.Monetary(string='Total Scheduled', compute='_compute_totals', store=True)
    total_paid = fields.Monetary(string='Total Paid', compute='_compute_totals', store=True)
    total_outstanding = fields.Monetary(string='Total Outstanding', compute='_compute_totals', store=True)
    overdue_count = fields.Integer(string='Overdue Installments', compute='_compute_totals', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True, required=True, copy=False)

    company_id = fields.Many2one(related='sale_agreement_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Plan Number must be unique per company.'),
    ]

    @api.depends('total_amount', 'down_payment', 'booking_amount')
    def _compute_financeable_amount(self):
        for rec in self:
            rec.financeable_amount = rec.total_amount - rec.down_payment - rec.booking_amount

    @api.depends('installment_ids.amount', 'installment_ids.paid_amount', 'installment_ids.status')
    def _compute_totals(self):
        for rec in self:
            rec.total_scheduled = sum(rec.installment_ids.mapped('amount'))
            rec.total_paid = sum(rec.installment_ids.mapped('paid_amount'))
            rec.total_outstanding = rec.total_scheduled - rec.total_paid
            rec.overdue_count = len(rec.installment_ids.filtered(lambda i: i.status == 'overdue'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.installment.plan') or 'New'
        return super().create(vals_list)

    @api.constrains('sale_agreement_id', 'state')
    def _check_single_active_plan_per_agreement(self):
        for rec in self:
            if rec.state == 'cancelled':
                continue
            other = self.search([
                ('sale_agreement_id', '=', rec.sale_agreement_id.id),
                ('state', '!=', 'cancelled'),
                ('id', '!=', rec.id),
            ], limit=1)
            if other:
                raise ValidationError(
                    'Sale Agreement "%s" already has an active Installment Plan '
                    '(%s). Cancel it before creating a new one.' % (
                        rec.sale_agreement_id.name, other.name))

    def action_generate_schedule(self):
        for rec in self:
            if rec.plan_type != 'equal':
                raise UserError('Automatic schedule generation only applies to '
                                 'Equal Installment plans. Add milestone lines manually.')
            if rec.installment_ids:
                raise UserError('This plan already has installment lines. Delete '
                                 'them first if you want to regenerate.')
            if rec.number_of_installments <= 0:
                raise UserError('Number of Installments must be greater than zero.')
            if not rec.start_date:
                raise UserError('Set a Start Date before generating the schedule.')

            n = rec.number_of_installments
            base_amount = round(rec.financeable_amount / n, 2)
            lines = []
            due_date = rec.start_date
            running_total = 0.0
            for i in range(1, n + 1):
                amount = base_amount
                if i == n:
                    # last installment absorbs any rounding remainder
                    amount = round(rec.financeable_amount - running_total, 2)
                running_total += amount
                lines.append((0, 0, {
                    'installment_number': i,
                    'due_date': due_date,
                    'amount': amount,
                    'status': 'upcoming',
                }))
                due_date = rec._next_due_date(due_date)
            rec.installment_ids = lines

    def _next_due_date(self, current_date):
        self.ensure_one()
        if self.frequency == 'monthly':
            return current_date + relativedelta(months=1)
        if self.frequency == 'quarterly':
            return current_date + relativedelta(months=3)
        if self.frequency == 'half_yearly':
            return current_date + relativedelta(months=6)
        if self.frequency == 'yearly':
            return current_date + relativedelta(years=1)
        if self.frequency == 'custom':
            return current_date + relativedelta(days=self.custom_interval_days or 30)
        return current_date + relativedelta(months=1)

    def action_activate(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft plans can be activated.')
            if not rec.installment_ids:
                raise UserError('Add or generate at least one installment line first.')
            if round(rec.total_scheduled, 2) > round(rec.financeable_amount, 2) + 0.01:
                raise UserError(
                    'Installment total (%.2f) cannot exceed the agreement amount '
                    'to schedule (%.2f) on plan "%s".' % (
                        rec.total_scheduled, rec.financeable_amount, rec.name))
        self.write({'state': 'active'})

    def action_complete(self):
        for rec in self:
            if rec.state != 'active':
                raise UserError('Only active plans can be completed.')
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_recompute_statuses(self):
        self.installment_ids._compute_status_now()
