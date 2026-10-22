# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentTrimBom(models.Model):
    """Trim BOM (SRS section 11) — garment.trim.bom. Covers thread, zipper,
    button, label and other accessories with type-conditional fields."""
    _name = 'garment.trim.bom'
    _description = 'Garment Trim BOM Line'
    _order = 'sequence'

    bom_id = fields.Many2one('garment.bom', string='BOM', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    trim_type = fields.Selection([
        ('thread', 'Thread'), ('zipper', 'Zipper'), ('button', 'Button'), ('label', 'Label'),
        ('elastic', 'Elastic'), ('snap', 'Snap'), ('drawcord', 'Drawcord'), ('eyelet', 'Eyelet'),
        ('tape', 'Tape'), ('buckle', 'Buckle'), ('hook_loop', 'Hook & Loop'),
        ('interlining', 'Interlining'), ('accessory', 'Other Accessory'),
    ], string='Trim Type', required=True)
    description = fields.Char(string='Description')
    color = fields.Char(string='Color')
    size_spec = fields.Char(string='Size / Spec')

    # Thread-specific
    thread_count = fields.Char(string='Thread Count')
    thread_type = fields.Char(string='Thread Type')
    thread_brand = fields.Char(string='Thread Brand')

    # Zipper-specific
    zipper_length = fields.Char(string='Zipper Length')
    zipper_type = fields.Char(string='Zipper Type')
    zipper_slider_type = fields.Char(string='Slider Type')

    # Button-specific
    button_size = fields.Char(string='Button Size (Ligne)')
    button_material = fields.Char(string='Button Material')
    button_type = fields.Char(string='Button Type')
    button_hole_type = fields.Selection([
        ('2_hole', '2 Hole'), ('4_hole', '4 Hole'), ('shank', 'Shank'), ('other', 'Other'),
    ], string='Hole Type')

    # Label-specific
    label_type = fields.Char(string='Label Type')
    label_material = fields.Char(string='Label Material')
    label_artwork_reference = fields.Char(string='Artwork Reference')
    label_position = fields.Char(string='Position')

    supplier_id = fields.Many2one('res.partner', string='Supplier')
    uom = fields.Char(string='UoM')
    consumption_per_piece = fields.Float(string='Consumption Per Piece')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='bom_id.currency_id', store=True)
    required_qty = fields.Float(string='Total Required Qty', compute='_compute_line', store=True)
    line_cost = fields.Monetary(string='Line Cost', compute='_compute_line', store=True, currency_field='currency_id')

    # Buyer requirements / compliance (SRS section 4.4 / 36)
    buyer_material_code = fields.Char(string='Buyer Material Code')
    buyer_description = fields.Char(string='Buyer Description')
    is_restricted = fields.Boolean(string='Restricted Material')
    restriction_reason = fields.Char(string='Restriction Reason')
    compliance_oekotex = fields.Boolean(string='OEKO-TEX')
    compliance_chemical_status = fields.Selection([
        ('compliant', 'Compliant'), ('pending', 'Pending'), ('non_compliant', 'Non-Compliant'),
    ], string='Chemical Compliance', default='pending')

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
