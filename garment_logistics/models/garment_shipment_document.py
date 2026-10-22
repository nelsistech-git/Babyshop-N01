# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from datetime import timedelta

from odoo import api, fields, models


class GarmentShipmentDocument(models.Model):
    """Shipment Document Management (SRS section 33) —
    garment.shipment.document."""
    _name = 'garment.shipment.document'
    _description = 'Garment Shipment Document'
    _order = 'upload_date desc'

    shipment_id = fields.Many2one('garment.shipment', string='Shipment', required=True, ondelete='cascade')
    document_type = fields.Selection([
        ('bill_of_lading', 'Bill of Lading'), ('airway_bill', 'Airway Bill'),
        ('delivery_order', 'Delivery Order'), ('shipping_instruction', 'Shipping Instructions'),
        ('freight_invoice', 'Freight Invoice'), ('other', 'Other'),
    ], string='Document Type', required=True)
    name = fields.Char(string='Document Name', required=True)
    file = fields.Binary(string='File', attachment=True, required=True)
    filename = fields.Char(string='Filename')
    upload_date = fields.Date(string='Upload Date', default=fields.Date.context_today)
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
    ], string='Approval Status', default='draft')
    shared_with_buyer = fields.Boolean(string='Shared with Buyer')
    expiry_date = fields.Date(string='Expiry Date')
    is_expiring_soon = fields.Boolean(string='Expiring Soon', compute='_compute_is_expiring_soon', store=True)

    @api.depends('expiry_date')
    def _compute_is_expiring_soon(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_expiring_soon = bool(rec.expiry_date and rec.expiry_date <= today + timedelta(days=15))
