# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateBooking(models.Model):
    """A customer's reservation of a specific unit. Becoming Confirmed is
    the point at which the 'one active booking per unit' rule (promised
    as a Phase 2 forward-reference) is enforced, and the Unit status
    moves to 'Booked'."""
    _name = 'real.estate.booking'
    _description = 'Real Estate Property Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Booking Number', copy=False, tracking=True,
                        default='New', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True,
                                   tracking=True, ondelete='restrict')
    project_id = fields.Many2one('real.estate.project', string='Project',
                                  related='unit_id.project_id', store=True, readonly=True)
    unit_id = fields.Many2one('real.estate.unit', string='Unit', required=True,
                               tracking=True, ondelete='restrict')

    booking_date = fields.Date(string='Booking Date', default=fields.Date.context_today)
    salesperson_id = fields.Many2one('res.users', string='Salesperson',
                                      default=lambda self: self.env.user)

    sale_price = fields.Monetary(string='Sale Price')
    discount = fields.Monetary(string='Discount')
    additional_charges = fields.Monetary(string='Additional Charges')
    final_price = fields.Monetary(string='Final Price', compute='_compute_final_price', store=True)

    booking_amount = fields.Monetary(string='Booking Amount', tracking=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('cheque', 'Cheque'),
        ('mobile_banking', 'Mobile Banking'),
        ('online_transfer', 'Online Transfer'),
        ('payment_gateway', 'Payment Gateway'),
    ], string='Payment Method')

    sale_agreement_id = fields.Many2one('real.estate.sale.agreement', string='Sale Agreement',
                                         readonly=True, copy=False)
    notes = fields.Text(string='Notes')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_booking_ir_attachment_rel',
        'booking_id', 'attachment_id', string='Documents')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True, required=True, copy=False)

    company_id = fields.Many2one(related='unit_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.depends('sale_price', 'additional_charges', 'discount')
    def _compute_final_price(self):
        for rec in self:
            rec.final_price = rec.sale_price + rec.additional_charges - rec.discount

    @api.onchange('unit_id')
    def _onchange_unit_id(self):
        if self.unit_id:
            self.sale_price = self.unit_id.final_price

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.booking') or 'New'
        return super().create(vals_list)

    def _require_state(self, expected):
        for rec in self:
            if rec.state != expected:
                raise UserError('Booking "%s" must be in state "%s" for this '
                                 'action (currently "%s").' % (rec.name, expected, rec.state))

    def action_submit(self):
        self._require_state('draft')
        self.write({'state': 'submitted'})

    def action_approve(self):
        self._require_state('submitted')
        self.write({'state': 'approved'})

    def action_confirm(self):
        self._require_state('approved')
        for rec in self:
            rec.unit_id.check_single_active_booking(exclude_booking_id=rec.id)
        self.write({'state': 'confirmed'})
        for rec in self:
            rec.unit_id.write({'status': 'booked'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'cancelled':
                raise UserError('This booking is already cancelled.')
        for rec in self:
            was_confirmed = rec.state == 'confirmed'
            rec.write({'state': 'cancelled'})
            if was_confirmed and rec.unit_id.status == 'booked':
                rec.unit_id.write({'status': 'available'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
