# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Line fields restricted once the parent order is locked after confirmation
# (SRS section 44 - "Restricted changes: Quantity, Price ... Style
# Information"). Delivery date / style is guarded at header level too.
_LOCKED_LINE_FIELDS = {'quantity', 'unit_price', 'style_id'}


class GarmentOrderLine(models.Model):
    """Order Line (SRS section 10) - garment.order.line.

    One order can carry multiple styles: each line is a Style / Color /
    Size-Range / Quantity / Unit Price row, e.g.
        Polo-101  Navy   20,000
        Polo-101  Black  15,000
        Polo-102  White  10,000
    """
    _name = 'garment.order.line'
    _description = 'Garment Order Line (Style / Color / Size / Qty)'
    _order = 'order_id, sequence, id'

    order_id = fields.Many2one('garment.order', string='Order', required=True, ondelete='cascade')
    order_state = fields.Selection(related='order_id.state', string='Order Status')
    sequence = fields.Integer(default=10)

    style_id = fields.Many2one('garment.style', string='Style', required=True)
    product_name = fields.Char(string='Product Name')
    color = fields.Char(string='Color', required=True)
    size_set_id = fields.Many2one('garment.size.set', string='Size Set')
    size_range = fields.Char(string='Size Range', help='e.g. S-XL')

    quantity = fields.Integer(string='Quantity', required=True)
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    total_value = fields.Monetary(string='Total Value', compute='_compute_total_value', store=True,
                                   currency_field='currency_id')
    delivery_date = fields.Date(string='Delivery Date')

    currency_id = fields.Many2one(related='order_id.currency_id', string='Currency', store=True, readonly=True)
    buyer_id = fields.Many2one(related='order_id.buyer_id', string='Buyer', store=True, readonly=True)

    color_ids = fields.One2many('garment.order.color', 'order_line_id', string='Color Details')
    size_ids = fields.One2many('garment.order.size', 'order_line_id', string='Size Breakdown')

    size_qty_total = fields.Integer(string='Size Breakdown Total', compute='_compute_size_qty_total')

    @api.depends('quantity', 'unit_price')
    def _compute_total_value(self):
        for rec in self:
            rec.total_value = (rec.quantity or 0) * (rec.unit_price or 0.0)

    @api.depends('size_ids.quantity')
    def _compute_size_qty_total(self):
        for rec in self:
            rec.size_qty_total = sum(rec.size_ids.mapped('quantity'))

    @api.onchange('style_id')
    def _onchange_style_id(self):
        if self.style_id:
            self.product_name = self.style_id.product_name or self.style_id.style_name

    def write(self, vals):
        is_manager = self.env.user.has_group('garment_order_management.group_order_manager')
        if not is_manager and any(f in _LOCKED_LINE_FIELDS for f in vals.keys()):
            for rec in self:
                if rec.order_id.is_locked:
                    raise UserError(_(
                        'Order "%s" is locked. Quantity, price and style changes require an Order '
                        'Revision (SRS section 44).') % rec.order_id.name)
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.order_id.is_locked and not self.env.user.has_group(
                    'garment_order_management.group_order_manager'):
                raise UserError(_('Order "%s" is locked - raise an Order Revision to remove a line.')
                                 % rec.order_id.name)
        return super().unlink()
