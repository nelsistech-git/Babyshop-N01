# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwOrderAllocation(models.Model):
    _name = 'fw.order.allocation'
    _description = 'Footwear Order Allocation (Buying House / Multi-Factory Split)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Allocation Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.order.allocation') or 'New')
    buyer_order_line_id = fields.Many2one('fw.buyer.order.line', string='Buyer Order Line',
                                           required=True, tracking=True)
    buyer_order_id = fields.Many2one(related='buyer_order_line_id.order_id',
                                      string='Buyer Order', store=True)
    buyer_id = fields.Many2one(related='buyer_order_id.buyer_id', string='Buyer', store=True)
    style_id = fields.Many2one(related='buyer_order_line_id.style_id', string='Style',
                                store=True)
    color_id = fields.Many2one(related='buyer_order_line_id.color_id', string='Color',
                                store=True)
    order_qty = fields.Integer(related='buyer_order_line_id.total_qty', string='Order Line Qty',
                                store=True)

    allocation_date = fields.Date(string='Allocation Date', default=fields.Date.context_today)
    currency_id = fields.Many2one(related='buyer_order_id.currency_id', string='Currency',
                                   store=True)

    allocation_line_ids = fields.One2many('fw.order.allocation.line', 'allocation_id',
                                           string='Factory Allocation')
    total_allocated_qty = fields.Integer(string='Total Allocated Qty',
                                          compute='_compute_totals', store=True)
    unallocated_qty = fields.Integer(string='Unallocated Qty', compute='_compute_totals',
                                      store=True)
    fully_allocated = fields.Boolean(string='Fully Allocated', compute='_compute_totals',
                                      store=True)

    commission_type = fields.Selection([
        ('none', 'No Commission (Owned Production)'),
        ('fixed_per_pair', 'Fixed Amount per Pair'),
        ('percent_of_fob', 'Percentage of FOB Value'),
    ], string='Commission Basis', default='none')
    commission_rate = fields.Float(string='Commission Rate',
                                    help="Amount per pair, or percentage, depending on "
                                         "Commission Basis.")
    commission_amount = fields.Monetary(string='Commission Amount', compute='_compute_commission',
                                         store=True, currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.order.allocation') or 'New'
        return super().create(vals_list)

    @api.depends('allocation_line_ids.qty_allocated', 'order_qty')
    def _compute_totals(self):
        for rec in self:
            rec.total_allocated_qty = sum(rec.allocation_line_ids.mapped('qty_allocated'))
            rec.unallocated_qty = (rec.order_qty or 0) - rec.total_allocated_qty
            rec.fully_allocated = rec.total_allocated_qty >= (rec.order_qty or 0) \
                and rec.order_qty > 0

    @api.depends('commission_type', 'commission_rate', 'total_allocated_qty',
                 'buyer_order_line_id.amount')
    def _compute_commission(self):
        for rec in self:
            if rec.commission_type == 'fixed_per_pair':
                rec.commission_amount = rec.total_allocated_qty * (rec.commission_rate or 0.0)
            elif rec.commission_type == 'percent_of_fob':
                line_value = rec.buyer_order_line_id.amount or 0.0
                rec.commission_amount = line_value * (rec.commission_rate or 0.0) / 100.0
            else:
                rec.commission_amount = 0.0

    def action_confirm(self):
        for rec in self:
            if not rec.allocation_line_ids:
                raise UserError("Cannot confirm an allocation with no factory lines.")
            if rec.total_allocated_qty > rec.order_qty:
                raise UserError(
                    "Total allocated quantity (%d) exceeds the order line quantity (%d)."
                    % (rec.total_allocated_qty, rec.order_qty))
        self.write({'state': 'confirmed'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class FwOrderAllocationLine(models.Model):
    _name = 'fw.order.allocation.line'
    _description = 'Footwear Order Allocation Factory Line'
    _order = 'sequence, id'

    allocation_id = fields.Many2one('fw.order.allocation', string='Allocation', required=True,
                                     ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    factory_id = fields.Many2one('fw.factory', string='Factory', required=True)
    relationship_type = fields.Selection(related='factory_id.relationship_type',
                                          string='Relationship', store=True)

    qty_allocated = fields.Integer(string='Qty Allocated', required=True, default=0)
    currency_id = fields.Many2one(related='allocation_id.currency_id', string='Currency',
                                   store=True)
    unit_cost = fields.Monetary(string='Unit Cost / CMT Rate', currency_field='currency_id',
                                 help="For Owned: your Cut & Make cost per pair. "
                                      "For Subcontractor: the CMT conversion fee per pair. "
                                      "For External Vendor: the purchase price per pair.")
    line_amount = fields.Monetary(string='Line Amount', compute='_compute_line_amount',
                                   store=True, currency_field='currency_id')

    production_order_id = fields.Many2one(
        'fw.production.order', string='Production Order (Owned)',
        help="Link to the FW Advanced Manufacturing Production Order for this slice, "
             "if produced in-house.")
    subcontract_order_id = fields.Many2one('fw.subcontract.order', string='Subcontract Order',
                                            readonly=True, copy=False)

    @api.onchange('factory_id')
    def _onchange_factory_id(self):
        if self.factory_id and self.factory_id.relationship_type == 'subcontractor':
            self.unit_cost = self.factory_id.default_conversion_rate

    @api.depends('qty_allocated', 'unit_cost')
    def _compute_line_amount(self):
        for rec in self:
            rec.line_amount = (rec.qty_allocated or 0) * (rec.unit_cost or 0.0)

    @api.constrains('qty_allocated', 'unit_cost')
    def _check_non_negative(self):
        for rec in self:
            if rec.qty_allocated < 0:
                raise ValidationError("Allocated quantity cannot be negative.")
            if rec.unit_cost < 0:
                raise ValidationError("Unit Cost / CMT Rate cannot be negative.")

    def action_create_subcontract_order(self):
        for rec in self:
            if rec.factory_id.relationship_type != 'subcontractor':
                raise UserError(
                    "'%s' is not marked as a Subcontractor factory. Set its Relationship "
                    "Type to Subcontractor (CMT) first." % rec.factory_id.name)
            if rec.subcontract_order_id:
                raise UserError("A Subcontract Order is already linked to this line.")
            sub_order = self.env['fw.subcontract.order'].create({
                'allocation_line_id': rec.id,
                'conversion_cost_per_pair': rec.unit_cost,
            })
            rec.subcontract_order_id = sub_order.id
