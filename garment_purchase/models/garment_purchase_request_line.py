# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentPurchaseRequestLine(models.Model):
    """Purchase Requisition Line (SRS sections 8, 10, 22, 26) —
    garment.purchase.request.line. Carries fabric-specific and
    accessory-specific fields directly, since standalone product-master
    models are not yet part of this suite."""
    _name = 'garment.purchase.request.line'
    _description = 'Garment Purchase Requisition Line'
    _order = 'sequence'

    requisition_id = fields.Many2one('garment.purchase.requisition', string='Requisition', required=True,
                                      ondelete='cascade')
    sequence = fields.Integer(default=10)
    material_category = fields.Selection([
        ('fabric', 'Fabric'), ('trim', 'Trim/Accessory'), ('packaging', 'Packaging'), ('other', 'Other'),
    ], string='Material Category', required=True)
    material_name = fields.Char(string='Material / Product', required=True)
    specification = fields.Char(string='Specification')

    # Fabric-specific (SRS section 22)
    composition = fields.Char(string='Composition')
    gsm = fields.Char(string='GSM')
    width = fields.Char(string='Width')
    color = fields.Char(string='Color')
    pantone_code = fields.Char(string='Pantone Code')
    consumption = fields.Float(string='Consumption')

    # Fabric Color Management (SRS section 23)
    buyer_color_code = fields.Char(string='Buyer Color Code')
    supplier_color_code = fields.Char(string='Supplier Color Code')
    shade_band = fields.Char(string='Shade Band')
    lab_dip_status = fields.Selection([
        ('not_required', 'Not Required'), ('requested', 'Lab Dip Requested'),
        ('submitted', 'Supplier Submission Received'), ('buyer_approved', 'Buyer Approved'),
        ('rejected', 'Rejected'),
    ], string='Lab Dip Status', default='not_required',
        help='Color Requirement -> Lab Dip Request -> Supplier Submission -> Buyer Approval -> '
             'Bulk Fabric Production (SRS section 23 color workflow).')
    color_approval_status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Color Approval Status', default='pending')

    # Accessory-specific (SRS section 26)
    accessory_size = fields.Char(string='Accessory Size')
    accessory_color = fields.Char(string='Accessory Color')
    accessory_material = fields.Char(string='Accessory Material')
    brand_requirement = fields.Char(string='Brand Requirement', help='e.g. YKK for zippers.')
    buyer_approval_status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Buyer Approval (Accessory)', default='pending')
    supplier_specification = fields.Text(string='Supplier Specification')

    uom = fields.Char(string='UoM')
    required_qty = fields.Float(string='Required Quantity', required=True)
    available_stock = fields.Float(string='Available Stock')
    incoming_stock = fields.Float(string='Incoming Stock')
    purchase_qty = fields.Float(string='Purchase Required Quantity', compute='_compute_purchase_qty', store=True,
                                 help='Required Material - Available Stock - Incoming Stock (SRS section 10).')
    shortage_qty = fields.Float(string='Shortage', compute='_compute_purchase_qty', store=True)
    is_shortage = fields.Boolean(string='Is Shortage', compute='_compute_purchase_qty', store=True)

    supplier_id = fields.Many2one('res.partner', string='Preferred Supplier')
    delivery_date = fields.Date(string='Delivery Date')

    @api.depends('required_qty', 'available_stock', 'incoming_stock')
    def _compute_purchase_qty(self):
        for rec in self:
            purchase_needed = (rec.required_qty or 0.0) - (rec.available_stock or 0.0) - (rec.incoming_stock or 0.0)
            rec.purchase_qty = max(0.0, purchase_needed)
            rec.shortage_qty = max(0.0, purchase_needed)
            rec.is_shortage = rec.shortage_qty > 0
