# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentShipmentAllocation(models.Model):
    """Shipment Allocation (SRS section 9) — garment.shipment.allocation."""
    _name = 'garment.shipment.allocation'
    _description = 'Garment Shipment Allocation'
    _order = 'sequence'

    shipment_id = fields.Many2one('garment.shipment', string='Shipment', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    style_id = fields.Many2one('garment.style', string='Style', required=True)
    po_reference = fields.Char(string='PO Reference')
    required_qty = fields.Integer(string='Required Quantity')
    allocated_qty = fields.Integer(string='Allocated Quantity')
    carton_qty = fields.Integer(string='Carton Quantity')
    warehouse_location = fields.Char(string='Warehouse Location')
    status = fields.Selection([
        ('pending', 'Pending'), ('partial', 'Partially Allocated'), ('ready', 'Ready'),
    ], string='Status', compute='_compute_status', store=True)

    @api.depends('required_qty', 'allocated_qty')
    def _compute_status(self):
        for rec in self:
            if not rec.allocated_qty:
                rec.status = 'pending'
            elif rec.allocated_qty >= (rec.required_qty or 0):
                rec.status = 'ready'
            else:
                rec.status = 'partial'
