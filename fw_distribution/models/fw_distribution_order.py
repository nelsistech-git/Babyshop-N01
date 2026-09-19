# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwDistributionOrder(models.Model):
    _name = 'fw.distribution.order'
    _description = 'Footwear Distribution Sales Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'order_date desc'

    name = fields.Char(string='Order Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.distribution.order') or 'New')
    channel_partner_id = fields.Many2one('fw.channel.partner', string='Dealer/Distributor',
                                          required=True, tracking=True)
    channel_type = fields.Selection(related='channel_partner_id.channel_type',
                                     string='Channel Type', store=True)

    order_date = fields.Date(string='Order Date', default=fields.Date.context_today)
    delivery_date = fields.Date(string='Delivery Date')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    line_ids = fields.One2many('fw.distribution.order.line', 'order_id', string='Order Lines')

    total_qty = fields.Integer(string='Total Qty (Pairs)', compute='_compute_totals', store=True)
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_totals', store=True,
                                    currency_field='currency_id')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.distribution.order') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.qty', 'line_ids.amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_qty = sum(rec.line_ids.mapped('qty'))
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Cannot confirm an order with no order lines.")
        self.write({'state': 'confirmed'})

    def action_deliver(self):
        self.write({'state': 'delivered'})

    def action_invoice(self):
        self.write({'state': 'invoiced'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class FwDistributionOrderLine(models.Model):
    _name = 'fw.distribution.order.line'
    _description = 'Footwear Distribution Order Line'
    _order = 'sequence, id'

    order_id = fields.Many2one('fw.distribution.order', string='Order', required=True,
                                ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    style_id = fields.Many2one('fw.style', string='Style', required=True)
    color_id = fields.Many2one('fw.color', string='Color')
    size_curve_id = fields.Many2one('fw.size.curve', string='Size Curve')
    qty = fields.Integer(string='Qty (Pairs)', required=True, default=0)
    unit_price = fields.Float(string='Unit Price', digits='Product Price')
    currency_id = fields.Many2one(related='order_id.currency_id', string='Currency', store=True)
    amount = fields.Monetary(string='Amount', compute='_compute_amount', store=True,
                              currency_field='currency_id')

    @api.depends('qty', 'unit_price')
    def _compute_amount(self):
        for rec in self:
            rec.amount = (rec.qty or 0) * (rec.unit_price or 0.0)

    @api.constrains('qty', 'unit_price')
    def _check_non_negative(self):
        for rec in self:
            if rec.qty < 0:
                raise ValidationError("Order line quantity cannot be negative.")
            if rec.unit_price < 0:
                raise ValidationError("Order line unit price cannot be negative.")

    @api.onchange('style_id')
    def _onchange_style_id(self):
        if self.style_id:
            if self.style_id.size_curve_id:
                self.size_curve_id = self.style_id.size_curve_id
            if not self.unit_price and self.style_id.last_price:
                self.unit_price = self.style_id.last_price
