# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentPurchaseFabricBooking(models.Model):
    """Fabric Booking Management (SRS section 24) —
    garment.purchase.fabric.booking. Reserves fabric capacity with a
    supplier ahead of full purchase-order confirmation, referencing the
    Buyer/Style/Order this booking is for."""
    _name = 'garment.purchase.fabric.booking'
    _description = 'Garment Fabric Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'delivery_date'

    booking_number = fields.Char(string='Booking Number', copy=False, readonly=True, default=lambda s: _('New'))
    buyer_id = fields.Many2one('garment.buyer', string='Buyer')
    style_id = fields.Many2one('garment.style', string='Style')
    order_id = fields.Many2one('garment.order', string='Order')
    requisition_id = fields.Many2one('garment.purchase.requisition', string='Purchase Requisition')
    fabric_type = fields.Char(string='Fabric Type', required=True)
    composition = fields.Char(string='Composition')
    gsm = fields.Char(string='GSM')
    width = fields.Char(string='Width')
    quantity = fields.Float(string='Booking Quantity', required=True)
    uom = fields.Char(string='UoM', default='KG')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True)
    delivery_date = fields.Date(string='Delivery Date')
    order_ref_id = fields.Many2one('garment.purchase.order', string='Confirmed Purchase Order', copy=False)

    status = fields.Selection([
        ('draft', 'Draft'), ('booked', 'Booked'), ('confirmed', 'Confirmed to PO'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('booking_number', _('New')) == _('New'):
                vals['booking_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.purchase.fabric.booking') or _('New')
        return super().create(vals_list)

    def action_confirm_booking(self):
        self.write({'status': 'booked'})

    def action_cancel_booking(self):
        self.write({'status': 'cancelled'})
