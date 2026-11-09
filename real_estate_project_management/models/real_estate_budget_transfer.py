# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class RealEstateBudgetTransfer(models.Model):
    """Moves allocated budget from one budget-head line to another.
    Never mutates history silently - each transfer is its own audited
    record, and amounts only move once the transfer is approved."""
    _name = 'real.estate.budget.transfer'
    _description = 'Real Estate Budget Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Transfer Number', copy=False, tracking=True,
                        default='New', readonly=True)
    source_allocation_id = fields.Many2one('real.estate.budget.allocation',
                                            string='Source Allocation', required=True,
                                            tracking=True, ondelete='restrict')
    destination_allocation_id = fields.Many2one('real.estate.budget.allocation',
                                                 string='Destination Allocation', required=True,
                                                 tracking=True, ondelete='restrict')
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    reason = fields.Text(string='Reason', required=True)
    requested_by = fields.Many2one('res.users', string='Requested By',
                                    default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    date = fields.Date(string='Date', default=fields.Date.context_today)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='State', default='draft', tracking=True, required=True, copy=False)

    company_id = fields.Many2one(related='source_allocation_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='source_allocation_id.currency_id', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.budget.transfer') or 'New'
        return super().create(vals_list)

    @api.constrains('source_allocation_id', 'destination_allocation_id')
    def _check_different_lines(self):
        for rec in self:
            if rec.source_allocation_id == rec.destination_allocation_id:
                raise ValidationError('Source and Destination allocation must be different.')

    @api.constrains('amount')
    def _check_amount_positive(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError('Transfer amount must be greater than zero.')

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft transfers can be submitted.')
        self.write({'state': 'submitted'})

    def action_approve(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError('Only submitted transfers can be approved.')
            if rec.amount > rec.source_allocation_id.allocated_amount:
                raise UserError(
                    'Cannot transfer %.2f: source allocation "%s" only has '
                    '%.2f allocated.' % (
                        rec.amount, rec.source_allocation_id.budget_head,
                        rec.source_allocation_id.allocated_amount))
        for rec in self:
            rec.source_allocation_id.allocated_amount -= rec.amount
            rec.destination_allocation_id.allocated_amount += rec.amount
            rec.write({'state': 'approved', 'approved_by': self.env.user.id})

    def action_reject(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError('Only submitted transfers can be rejected.')
        self.write({'state': 'rejected'})

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == 'approved':
                raise UserError('An approved transfer cannot be reset to draft; '
                                 'its amounts have already moved. Create a '
                                 'reversing transfer instead.')
        self.write({'state': 'draft'})
