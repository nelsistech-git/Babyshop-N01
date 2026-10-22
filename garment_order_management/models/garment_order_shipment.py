# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentOrderShipment(models.Model):
    """Order Shipment / Partial Shipment Management (SRS sections 28-30) -
    garment.order.shipment. Supports splitting an order across multiple
    shipments (e.g. PO-5001 -> Shipment 1: 50,000 / Shipment 2: 30,000 /
    Shipment 3: 20,000) and tracks shipped vs. balance quantity.
    """
    _name = 'garment.order.shipment'
    _description = 'Garment Order Shipment'
    _order = 'order_id, sequence, id'

    order_id = fields.Many2one('garment.order', string='Order', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Shipment Reference', compute='_compute_name', store=True)

    planned_date = fields.Date(string='Planned Shipment Date')
    actual_shipment_date = fields.Date(string='Actual Shipment Date')
    shipment_qty = fields.Integer(string='Shipment Quantity', required=True)
    shipped_qty = fields.Integer(string='Shipped Quantity', help='Actually shipped, once dispatched.')
    pending_qty = fields.Integer(string='Pending Quantity', compute='_compute_pending_qty', store=True)

    status = fields.Selection([
        ('planned', 'Planned'), ('in_production', 'In Production'), ('ready', 'Ready'),
        ('shipped', 'Shipped'), ('delayed', 'Delayed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='planned')

    port_of_loading = fields.Char(string='Port of Loading')
    port_of_destination = fields.Char(string='Port of Destination')
    shipment_mode = fields.Selection([
        ('sea', 'Sea'), ('air', 'Air'), ('courier', 'Courier'), ('multimodal', 'Multimodal'),
    ], string='Shipment Mode')
    vessel_flight_ref = fields.Char(string='Vessel / Flight Reference')
    remarks = fields.Text(string='Remarks')

    @api.depends('order_id.name', 'sequence')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s / Shipment %s' % (rec.order_id.name or _('New'), rec.sequence)

    @api.depends('shipment_qty', 'shipped_qty', 'status')
    def _compute_pending_qty(self):
        for rec in self:
            actually_shipped = rec.shipped_qty if rec.status == 'shipped' else 0
            rec.pending_qty = (rec.shipment_qty or 0) - (actually_shipped or 0)

