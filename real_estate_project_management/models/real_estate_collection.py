# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateCollection(models.Model):
    """A payment receipt against an installment (or an on-account payment
    with no specific installment). Confirming it is what actually moves
    the linked installment's paid_amount/status forward - Collection is
    the single source of truth for 'has this been paid'."""
    _name = 'real.estate.collection'
    _description = 'Real Estate Payment Collection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Receipt Number', copy=False, tracking=True,
                        default='New', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True,
                                   tracking=True, ondelete='restrict')
    sale_agreement_id = fields.Many2one('real.estate.sale.agreement', string='Sale Agreement',
                                         tracking=True,
                                         domain="[('customer_id', '=', customer_id)]")
    project_id = fields.Many2one('real.estate.project', string='Project',
                                  compute='_compute_project_unit', store=True, readonly=True)
    unit_id = fields.Many2one('real.estate.unit', string='Unit',
                               compute='_compute_project_unit', store=True, readonly=True)
    installment_id = fields.Many2one('real.estate.installment', string='Installment',
                                      domain="[('customer_id', '=', customer_id)]")

    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, tracking=True)
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('cheque', 'Cheque'),
        ('mobile_banking', 'Mobile Banking'),
        ('online_transfer', 'Online Transfer'),
        ('payment_gateway', 'Payment Gateway'),
    ], string='Payment Method', required=True, default='bank')
    bank = fields.Char(string='Bank')
    cheque_number = fields.Char(string='Cheque Number')
    transaction_id = fields.Char(string='Transaction ID')
    reference = fields.Char(string='Reference')
    collector_id = fields.Many2one('res.users', string='Collector', default=lambda self: self.env.user)

    allow_overpayment = fields.Boolean(
        string='Allow Overpayment (with authorization)', default=False,
        help='If disabled, this receipt is blocked from exceeding the '
             'linked installment\'s outstanding amount.')

    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_collection_ir_attachment_rel',
        'collection_id', 'attachment_id', string='Attachments')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True, required=True, copy=False)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.onchange('installment_id')
    def _onchange_installment_id(self):
        if self.installment_id:
            self.amount = self.installment_id.due_amount
            self.sale_agreement_id = self.installment_id.plan_id.sale_agreement_id

    @api.depends('sale_agreement_id', 'sale_agreement_id.project_id', 'sale_agreement_id.unit_id')
    def _compute_project_unit(self):
        for rec in self:
            if rec.sale_agreement_id:
                rec.project_id = rec.sale_agreement_id.project_id
                rec.unit_id = rec.sale_agreement_id.unit_id
            else:
                rec.project_id = False
                rec.unit_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.collection') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft receipts can be confirmed.')
            if rec.amount <= 0:
                raise UserError('Payment amount must be greater than zero.')
            if rec.installment_id and not rec.allow_overpayment:
                if rec.amount > rec.installment_id.due_amount + 0.01:
                    raise UserError(
                        'Payment of %.2f exceeds the outstanding amount of %.2f '
                        'on "%s". Enable "Allow Overpayment" to proceed anyway.' % (
                            rec.amount, rec.installment_id.due_amount,
                            rec.installment_id.display_name))
        self.write({'state': 'confirmed'})
        self.mapped('installment_id')._compute_status_now()

    def action_cancel(self):
        for rec in self:
            if rec.state == 'cancelled':
                raise UserError('This receipt is already cancelled.')
        self.write({'state': 'cancelled'})
        self.mapped('installment_id')._compute_status_now()

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError('A confirmed receipt cannot be reset to draft; '
                                 'cancel it and create a new one instead.')
        self.write({'state': 'draft'})
