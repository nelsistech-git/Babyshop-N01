# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class RealEstateCommission(models.Model):
    """One commission payable on one Sale Agreement to one beneficiary at
    one layer (Level 1 / Level 2). Generated automatically when the sale
    agreement is activated (amount / percent taken from the commission rules)
    and editable by managers before approval."""
    _name = 'real.estate.commission'
    _description = 'Real Estate Commission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Commission No.', default='New', copy=False, readonly=True)
    sale_agreement_id = fields.Many2one('real.estate.sale.agreement', string='Sale Agreement',
                                         required=True, ondelete='cascade', index=True, tracking=True)
    customer_id = fields.Many2one(related='sale_agreement_id.customer_id', string='Buyer',
                                   store=True, readonly=True)
    project_id = fields.Many2one(related='sale_agreement_id.project_id', store=True, readonly=True)
    unit_id = fields.Many2one(related='sale_agreement_id.unit_id', store=True, readonly=True)
    agent_id = fields.Many2one(related='sale_agreement_id.agent_id', string='Sold By',
                                store=True, readonly=True)

    level = fields.Selection([
        ('1', 'Level 1 (Direct)'),
        ('2', 'Level 2 (Upline)'),
    ], string='Layer', required=True, tracking=True)
    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary', required=True,
                                      ondelete='restrict', tracking=True, index=True)
    beneficiary_type = fields.Selection([('agent', 'Agent'), ('customer', 'Customer')],
                                         compute='_compute_beneficiary_type', string='Beneficiary Type')

    calc_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Calculation', required=True, default='percentage')
    rate_value = fields.Float(string='Percent / Amount', digits=(16, 2))
    base_amount = fields.Monetary(string='Sale Amount (Base)', compute='_compute_base_amount',
                                   store=True, readonly=False)
    amount = fields.Monetary(string='Commission Amount', compute='_compute_amount',
                              store=True, readonly=False, tracking=True)

    state = fields.Selection([
        ('draft', 'Pending Approval'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)
    approved_date = fields.Date(string='Approved On', copy=False)
    payment_date = fields.Date(string='Paid On', copy=False)
    payment_reference = fields.Char(string='Payment Reference', copy=False)
    notes = fields.Text(string='Notes')

    company_id = fields.Many2one(related='sale_agreement_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.depends('beneficiary_id.is_agent')
    def _compute_beneficiary_type(self):
        for rec in self:
            rec.beneficiary_type = 'agent' if rec.beneficiary_id.is_agent else 'customer'

    @api.depends('sale_agreement_id.net_price')
    def _compute_base_amount(self):
        for rec in self:
            rec.base_amount = rec.sale_agreement_id.net_price

    @api.depends('calc_type', 'rate_value', 'base_amount')
    def _compute_amount(self):
        for rec in self:
            if rec.calc_type == 'percentage':
                rec.amount = (rec.base_amount or 0.0) * (rec.rate_value or 0.0) / 100.0
            else:
                rec.amount = rec.rate_value or 0.0

    @api.constrains('sale_agreement_id', 'level', 'state')
    def _check_unique_level(self):
        for rec in self.filtered(lambda c: c.state != 'cancelled'):
            dup = self.search_count([
                ('id', '!=', rec.id), ('sale_agreement_id', '=', rec.sale_agreement_id.id),
                ('level', '=', rec.level), ('state', '!=', 'cancelled')])
            if dup:
                raise ValidationError(_(
                    'Agreement "%(agr)s" already has a Level %(lvl)s commission.',
                    agr=rec.sale_agreement_id.name, lvl=rec.level))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('real.estate.commission') or 'New'
        return super().create(vals_list)

    # ---- workflow ---------------------------------------------------
    def _require_state(self, states):
        for rec in self:
            if rec.state not in states:
                raise UserError(_('Commission "%(n)s" cannot do this from status "%(s)s".',
                                  n=rec.name, s=rec.state))

    def action_approve(self):
        self._require_state(('draft',))
        for rec in self:
            if rec.amount <= 0:
                raise UserError(_('Commission "%s" has a zero amount.') % rec.name)
        self.write({'state': 'approved', 'approved_date': fields.Date.context_today(self)})

    def action_mark_paid(self):
        self._require_state(('approved',))
        self.write({'state': 'paid', 'payment_date': fields.Date.context_today(self)})

    def action_cancel(self):
        self._require_state(('draft', 'approved'))
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self._require_state(('approved', 'cancelled'))
        self.write({'state': 'draft', 'approved_date': False})
