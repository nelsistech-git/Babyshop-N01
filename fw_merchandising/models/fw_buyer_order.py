# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwBuyerOrder(models.Model):
    _name = 'fw.buyer.order'
    _description = 'Footwear Buyer Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'order_date desc'

    name = fields.Char(string='Order Reference', required=True, copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code(
                           'fw.buyer.order') or 'New')
    buyer_po_no = fields.Char(string="Buyer's PO Number", tracking=True)
    buyer_id = fields.Many2one('fw.buyer', string='Buyer', required=True, tracking=True)
    season_id = fields.Many2one('fw.season', string='Season', tracking=True)
    factory_id = fields.Many2one('fw.factory', string='Factory', tracking=True)

    order_date = fields.Date(string='Order Date', default=fields.Date.context_today, tracking=True)
    ship_date = fields.Date(string='Required Ship Date', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_production', 'In Production'),
        ('shipped', 'Shipped'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    line_ids = fields.One2many('fw.buyer.order.line', 'order_id', string='Order Lines')
    tna_line_ids = fields.One2many('fw.tna.line', 'order_id', string='TNA Milestones')
    shipment_ids = fields.One2many('fw.shipment', 'order_id', string='Shipments')
    shipment_count = fields.Integer(string='Shipments', compute='_compute_shipment_count')

    total_qty = fields.Integer(string='Total Order Qty (Pairs)', compute='_compute_totals',
                               store=True)
    total_amount = fields.Monetary(string='Total Order Value', compute='_compute_totals',
                                   store=True, currency_field='currency_id')
    shipped_qty = fields.Integer(string='Total Shipped Qty', compute='_compute_shipped_qty')
    balance_qty = fields.Integer(string='Balance to Ship', compute='_compute_shipped_qty')

    delayed_tna_count = fields.Integer(string='Delayed Milestones', compute='_compute_delayed_tna', store=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.buyer.order') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.total_qty', 'line_ids.amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_qty = sum(rec.line_ids.mapped('total_qty'))
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    def _compute_shipment_count(self):
        for rec in self:
            rec.shipment_count = len(rec.shipment_ids)

    @api.depends('line_ids.total_qty')
    def _compute_shipped_qty(self):
        for rec in self:
            shipped = sum(rec.shipment_ids.mapped('line_ids').mapped('qty_shipped'))
            rec.shipped_qty = shipped
            rec.balance_qty = rec.total_qty - shipped

    @api.depends('tna_line_ids.status', 'tna_line_ids.planned_date')
    def _compute_delayed_tna(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.delayed_tna_count = len(rec.tna_line_ids.filtered(
                lambda t: t.status != 'done' and t.planned_date and t.planned_date < today))

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Cannot confirm an order with no order lines.")
        self.write({'state': 'confirmed'})

    def action_start_production(self):
        self.write({'state': 'in_production'})

    def action_mark_shipped(self):
        self.write({'state': 'shipped'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_shipments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shipments',
            'res_model': 'fw.shipment',
            'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }


class FwBuyerOrderLine(models.Model):
    _name = 'fw.buyer.order.line'
    _description = 'Footwear Buyer Order Line'
    _order = 'sequence, id'

    order_id = fields.Many2one('fw.buyer.order', string='Order', required=True,
                               ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    style_id = fields.Many2one('fw.style', string='Style', required=True)
    color_id = fields.Many2one('fw.color', string='Color')
    size_curve_id = fields.Many2one('fw.size.curve', string='Size Curve')
    total_qty = fields.Integer(string='Total Qty (Pairs)', required=True, default=0)
    unit_price = fields.Float(string='Unit FOB Price', digits='Product Price')
    currency_id = fields.Many2one(related='order_id.currency_id', string='Currency', store=True)
    amount = fields.Monetary(string='Line Amount', compute='_compute_amount', store=True,
                             currency_field='currency_id')

    @api.depends('total_qty', 'unit_price')
    def _compute_amount(self):
        for rec in self:
            rec.amount = (rec.total_qty or 0) * (rec.unit_price or 0.0)

    @api.constrains('total_qty', 'unit_price')
    def _check_non_negative(self):
        for rec in self:
            if rec.total_qty < 0:
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


class FwTnaLine(models.Model):
    _name = 'fw.tna.line'
    _description = 'Footwear TNA (Time & Action) Milestone'
    _order = 'order_id, sequence, planned_date'

    order_id = fields.Many2one('fw.buyer.order', string='Order', required=True,
                               ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    milestone = fields.Char(string='Milestone', required=True,
                            help="E.g. Order Confirmation, Fabric Booking, Fabric In-house, "
                                 "Cutting Start, Sewing Start, Ex-Factory")
    planned_date = fields.Date(string='Planned Date', required=True)
    actual_date = fields.Date(string='Actual Date')
    responsible_id = fields.Many2one('res.users', string='Responsible')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('delayed', 'Delayed'),
    ], string='Status', default='pending')
    remarks = fields.Char(string='Remarks')

    @api.onchange('actual_date')
    def _onchange_actual_date(self):
        for rec in self:
            if rec.actual_date:
                rec.status = 'done'
