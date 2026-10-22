# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentOrderAllocation(models.Model):
    """Multi-Factory / Order Split Allocation (SRS sections 14, 27-28) -
    garment.order.allocation. Tracks how the order quantity is split across
    factories / production lines / delivery dates (style-wise, color-wise,
    quantity-wise, factory-wise or shipment-wise, per SRS section 28).
    """
    _name = 'garment.order.allocation'
    _description = 'Garment Order Factory / Line Allocation'
    _order = 'order_id, sequence, id'

    order_id = fields.Many2one('garment.order', string='Order', required=True, ondelete='cascade')
    order_line_id = fields.Many2one('garment.order.line', string='Order Line (Style)',
                                     domain="[('order_id', '=', order_id)]")
    sequence = fields.Integer(default=10)

    split_type = fields.Selection([
        ('style', 'Style-wise'), ('color', 'Color-wise'), ('quantity', 'Quantity-wise'),
        ('factory', 'Factory-wise'), ('shipment', 'Shipment-wise'),
    ], string='Split Type', default='factory')

    factory = fields.Char(string='Factory', required=True)
    production_line = fields.Char(string='Production Line')
    allocated_qty = fields.Integer(string='Allocated Quantity', required=True)
    delivery_date = fields.Date(string='Delivery Date')

    production_status = fields.Selection([
        ('pending', 'Pending'), ('material_ready', 'Material Ready'), ('cutting', 'Cutting'),
        ('sewing', 'Sewing'), ('finishing', 'Finishing'), ('quality', 'Quality Inspection'),
        ('completed', 'Completed'),
    ], string='Production Status', default='pending')
