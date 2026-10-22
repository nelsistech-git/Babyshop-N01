# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import UserError


class CctvViolation(models.Model):
    _name = 'cctv.violation'
    _description = 'Employee Violation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True, index=True)
    event_id = fields.Many2one('cctv.event', string='Source AI Event',
                                help='Blank if this violation was raised manually rather than by AI detection')
    rule_id = fields.Many2one('cctv.violation.rule', tracking=True)
    category = fields.Selection(related='rule_id.category', store=True)
    violation_type = fields.Selection(related='rule_id.violation_type', store=True)

    office_id = fields.Many2one('cctv.office', string='Branch/Site')
    department_id = fields.Many2one('cctv.department')
    occurred_at = fields.Datetime(default=fields.Datetime.now, required=True)

    offense_number = fields.Integer(compute='_compute_offense_number', store=True,
                                     help='How many prior occurrences of this violation type this employee '
                                          'has had within the rule\'s reset window, plus this one')
    tier_id = fields.Many2one('cctv.violation.rule.tier', compute='_compute_tier', store=True)
    action_type = fields.Selection(related='tier_id.action_type', store=True, string='Proposed Action')
    proposed_fine = fields.Monetary(related='tier_id.fine_amount', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    approved_fine = fields.Monetary(currency_field='currency_id',
                                     help='HR can adjust the fine amount at approval time; defaults to the '
                                          'rule-proposed amount')

    # Evidence (mirrors the source event's snapshot for convenience)
    snapshot = fields.Binary(related='event_id.snapshot', readonly=True)
    ai_confidence = fields.Float(related='event_id.confidence', string='AI Confidence (%)', readonly=True)
    witness_ids = fields.Many2many('hr.employee', 'cctv_violation_witness_rel', 'violation_id', 'employee_id',
                                    string='Witnesses (optional)')

    state = fields.Selection([
        ('new', 'New (AI Detected)'),
        ('manager_review', 'Manager Review'),
        ('manager_rejected', 'Rejected by Manager'),
        ('hr_review', 'HR Review'),
        ('hr_rejected', 'Rejected by HR'),
        ('approved', 'Approved - Pending Processing'),
        ('processed', 'Processed (Action Taken)'),
        ('appealed', 'Under Appeal'),
        ('closed', 'Closed'),
    ], default='new', required=True, tracking=True)

    deduction_method = fields.Selection([
        ('warning_only', 'Warning Only (No Deduction)'),
        ('direct_salary', 'Direct Salary Deduction'),
        ('installment', 'Installment Deduction'),
        ('receivable', 'Separate Receivable (Employee Owes Company)'),
    ], default='warning_only', tracking=True)
    installment_months = fields.Integer(default=1)

    manager_notes = fields.Text()
    hr_notes = fields.Text()
    appeal_id = fields.Many2one('cctv.violation.appeal', readonly=True, copy=False)

    @api.depends('employee_id', 'violation_type', 'occurred_at')
    def _compute_display_name(self):
        for rec in self:
            label = dict(rec._fields['violation_type'].selection).get(rec.violation_type, 'Violation') \
                if rec.violation_type else 'Violation'
            rec.display_name = f"{rec.employee_id.name or ''} - {label} ({rec.occurred_at or ''})"

    @api.depends('employee_id', 'rule_id')
    def _compute_offense_number(self):
        for rec in self:
            if not rec.rule_id or not rec.employee_id:
                rec.offense_number = 1
                continue
            window_start = fields.Datetime.now() - relativedelta(months=rec.rule_id.reset_period_months)
            prior_count = self.search_count([
                ('id', '!=', rec.id),
                ('employee_id', '=', rec.employee_id.id),
                ('rule_id', '=', rec.rule_id.id),
                ('state', 'not in', ('manager_rejected', 'hr_rejected')),
                ('create_date', '>=', window_start),
            ])
            rec.offense_number = prior_count + 1

    @api.depends('rule_id', 'offense_number')
    def _compute_tier(self):
        for rec in self:
            rec.tier_id = rec.rule_id.get_tier_for_offense(rec.offense_number) if rec.rule_id else False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.state == 'new':
                rec.state = 'manager_review'
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary='Review CCTV violation',
                    note=f'{rec.display_name} needs manager review.',
                    user_id=(rec.employee_id.parent_id.user_id.id
                             or self.env.ref('base.user_admin').id),
                )
        return records

    # --- Manager step ---
    def action_manager_approve(self):
        for rec in self:
            if rec.state != 'manager_review':
                raise UserError('Only violations awaiting manager review can be approved at this step.')
            rec.state = 'hr_review'
            rec.approved_fine = rec.proposed_fine
            rec.activity_schedule(
                'mail.mail_activity_data_todo', summary='HR approval needed for CCTV violation',
                note=f'{rec.display_name} approved by manager, awaiting HR sign-off.')

    def action_manager_reject(self):
        self.write({'state': 'manager_rejected'})

    # --- HR step ---
    def action_hr_approve(self):
        for rec in self:
            if rec.state != 'hr_review':
                raise UserError('Only violations awaiting HR review can be approved at this step.')
        self.write({'state': 'approved'})

    def action_hr_reject(self):
        self.write({'state': 'hr_rejected'})

    def action_mark_processed(self):
        """HR/payroll confirms the fine/action was actually applied. This
        module does not auto-deduct wages - see README for why, and for how
        to export pending deductions to whatever payroll process you use."""
        for rec in self:
            if rec.state != 'approved':
                raise UserError('Only approved violations can be marked as processed.')
        self.write({'state': 'processed'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_submit_appeal(self, explanation):
        self.ensure_one()
        if self.appeal_id:
            raise UserError('This violation already has an appeal on file.')
        appeal = self.env['cctv.violation.appeal'].create({
            'violation_id': self.id,
            'employee_explanation': explanation,
        })
        self.write({'appeal_id': appeal.id, 'state': 'appealed'})
        return appeal

    @api.model
    def create_from_event(self, event):
        """Called from cctv.event.create() - matches the event's behavior_type
        against active violation rules scoped to the employee's office/department/
        job, and creates a violation if one matches. Silently does nothing if
        no person/employee is identified or no rule matches - this is meant to
        be safe to call on every event."""
        if not event.person_id or not event.person_id.employee_id:
            return False
        employee = event.person_id.employee_id
        domain = [
            ('violation_type', '=', event.behavior_type),
            ('active', '=', True),
            ('company_id', 'in', [employee.company_id.id, False]),
        ]
        rules = self.env['cctv.violation.rule'].search(domain)
        # Prefer the most specific rule: office+department+job > partial > company-wide
        def specificity(rule):
            return (
                (rule.office_id.id == event.office_id.id) if rule.office_id else False,
                (rule.department_id.id == event.department_id.id) if rule.department_id else False,
                (rule.job_id.id == employee.job_id.id) if rule.job_id else False,
            )
        matching = rules.filtered(lambda r: (
            (not r.office_id or r.office_id == event.office_id)
            and (not r.department_id or r.department_id == event.department_id)
            and (not r.job_id or r.job_id == employee.job_id)
        ))
        if not matching:
            return False
        rule = sorted(matching, key=specificity, reverse=True)[0]

        return self.create({
            'employee_id': employee.id,
            'event_id': event.id,
            'rule_id': rule.id,
            'office_id': event.office_id.id,
            'department_id': event.department_id.id,
            'occurred_at': event.event_time,
        })
