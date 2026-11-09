# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class RealEstateContractorBill(models.Model):
    """Contractor Work Certificate / Bill - measures completed work for a
    period and computes the net payable after retention/advance/deductions."""
    _name = 'real.estate.contractor.bill'
    _description = 'Real Estate Contractor Work Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Certificate Number', copy=False, tracking=True,
                        default='New', readonly=True)
    contractor_id = fields.Many2one('real.estate.contractor', string='Contractor',
                                     required=True, tracking=True, ondelete='restrict')
    project_id = fields.Many2one('real.estate.project', string='Project',
                                  related='contractor_id.project_id', store=True, readonly=True)
    work_package_id = fields.Many2one('real.estate.work.package', string='Work Package',
                                       domain="[('project_id', '=', project_id)]")

    period_start = fields.Date(string='Period Start')
    period_end = fields.Date(string='Period End')

    planned_quantity = fields.Float(string='Planned Quantity', digits=(12, 2))
    completed_quantity = fields.Float(string='Completed Quantity', digits=(12, 2))
    approved_quantity = fields.Float(string='Approved Quantity', digits=(12, 2))
    rate = fields.Monetary(string='Rate')

    gross_amount = fields.Monetary(string='Gross Amount', compute='_compute_amounts', store=True)
    retention_amount = fields.Monetary(string='Retention', compute='_compute_amounts', store=True)
    advance_adjustment = fields.Monetary(string='Advance Adjustment')
    deduction = fields.Monetary(string='Deduction')
    net_amount = fields.Monetary(string='Net Amount', compute='_compute_amounts', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('engineer_review', 'Engineer Review'),
        ('pm_approval', 'Project Manager Approval'),
        ('accounts', 'Accounts'),
        ('paid', 'Paid'),
    ], string='State', default='draft', tracking=True, required=True, copy=False)

    company_id = fields.Many2one(related='contractor_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.depends('approved_quantity', 'rate', 'advance_adjustment', 'deduction',
                 'contractor_id.retention_percentage')
    def _compute_amounts(self):
        for rec in self:
            gross = rec.approved_quantity * rec.rate
            retention = gross * (rec.contractor_id.retention_percentage or 0.0) / 100.0
            rec.gross_amount = gross
            rec.retention_amount = retention
            rec.net_amount = gross - retention - rec.advance_adjustment - rec.deduction

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.contractor.bill') or 'New'
        return super().create(vals_list)

    @api.constrains('period_start', 'period_end')
    def _check_period(self):
        for rec in self:
            if rec.period_start and rec.period_end and rec.period_end < rec.period_start:
                raise ValidationError('Period End cannot be before Period Start.')

    @api.constrains('approved_quantity', 'planned_quantity')
    def _check_approved_not_exceed_planned(self):
        for rec in self:
            if rec.planned_quantity and rec.approved_quantity > rec.planned_quantity:
                raise ValidationError(
                    'Approved Quantity (%.2f) cannot exceed Planned Quantity (%.2f) '
                    'on certificate "%s".' % (
                        rec.approved_quantity, rec.planned_quantity, rec.name))

    def _require_state(self, expected):
        for rec in self:
            if rec.state != expected:
                raise UserError('Certificate "%s" must be in state "%s" for this '
                                 'action (currently "%s").' % (rec.name, expected, rec.state))

    def action_submit(self):
        self._require_state('draft')
        self.write({'state': 'submitted'})

    def action_engineer_review(self):
        self._require_state('submitted')
        self.write({'state': 'engineer_review'})

    def action_pm_approve(self):
        self._require_state('engineer_review')
        self.write({'state': 'pm_approval'})

    def action_send_to_accounts(self):
        self._require_state('pm_approval')
        self.write({'state': 'accounts'})

    def action_mark_paid(self):
        self._require_state('accounts')
        self.write({'state': 'paid'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
