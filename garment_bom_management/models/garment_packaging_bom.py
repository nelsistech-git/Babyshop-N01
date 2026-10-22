# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentPackagingBom(models.Model):
    """Packaging BOM (SRS section 12-13) — garment.packaging.bom."""
    _name = 'garment.packaging.bom'
    _description = 'Garment Packaging BOM Line'
    _order = 'sequence'

    bom_id = fields.Many2one('garment.bom', string='BOM', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    packaging_type = fields.Selection([
        ('poly_bag', 'Poly Bag'), ('inner_carton', 'Inner Carton'), ('master_carton', 'Master Carton'),
        ('hang_tag', 'Hang Tag'), ('barcode', 'Barcode Sticker'), ('tissue', 'Tissue Paper'),
        ('hanger', 'Hanger'), ('silica_gel', 'Silica Gel'), ('pin', 'Pin'), ('clip', 'Clip'),
        ('insert_card', 'Insert Card'),
    ], string='Packaging Type', required=True)
    description = fields.Char(string='Description')
    packaging_size = fields.Char(string='Size')
    dimension = fields.Char(string='Dimension')
    weight = fields.Float(string='Weight (g)')
    material = fields.Char(string='Material')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    uom = fields.Char(string='UoM')
    consumption_per_piece = fields.Float(string='Consumption Per Piece', default=1.0)
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='bom_id.currency_id', store=True)
    required_qty = fields.Float(string='Total Required Qty', compute='_compute_line', store=True)
    line_cost = fields.Monetary(string='Line Cost', compute='_compute_line', store=True, currency_field='currency_id')

    # Buyer requirements (SRS section 4.4 / 36)
    buyer_material_code = fields.Char(string='Buyer Material Code')
    is_restricted = fields.Boolean(string='Restricted Material')
    restriction_reason = fields.Char(string='Restriction Reason')

    # Purchase / Inventory integration (SRS section 23-24)
    available_stock = fields.Float(string='Available Stock')
    incoming_stock = fields.Float(string='Incoming Stock')
    safety_stock = fields.Float(string='Safety Stock')
    purchase_qty = fields.Float(string='Purchase Quantity', compute='_compute_purchase_qty', store=True)

    @api.depends('consumption_per_piece', 'unit_price', 'bom_id.order_quantity')
    def _compute_line(self):
        for rec in self:
            order_qty = rec.bom_id.order_quantity or 0
            rec.required_qty = (rec.consumption_per_piece or 0.0) * order_qty
            rec.line_cost = rec.required_qty * (rec.unit_price or 0.0)

    @api.depends('required_qty', 'available_stock', 'incoming_stock', 'safety_stock')
    def _compute_purchase_qty(self):
        for rec in self:
            need = (rec.required_qty or 0.0) + (rec.safety_stock or 0.0) - (rec.available_stock or 0.0) \
                - (rec.incoming_stock or 0.0)
            rec.purchase_qty = max(need, 0.0)
