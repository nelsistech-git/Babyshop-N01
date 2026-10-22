# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentFabricBom(models.Model):
    """Fabric BOM (SRS section 9-10) — garment.fabric.bom. Net/gross
    consumption calculation with wastage breakdown by cause."""
    _name = 'garment.fabric.bom'
    _description = 'Garment Fabric BOM Line'
    _order = 'sequence'

    bom_id = fields.Many2one('garment.bom', string='BOM', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    fabric_code = fields.Char(string='Fabric Code')
    fabric_name = fields.Char(string='Fabric Name')
    fabric_role = fields.Selection([
        ('main', 'Main Fabric'), ('contrast', 'Contrast Fabric'), ('rib', 'Rib'), ('lining', 'Lining'),
        ('pocketing', 'Pocket Fabric'), ('interlining', 'Interlining'), ('padding', 'Padding'),
        ('mesh', 'Mesh'), ('fleece', 'Fleece'),
    ], string='Fabric Role', required=True)
    composition = fields.Char(string='Composition')
    gsm = fields.Char(string='GSM')
    width = fields.Char(string='Width')
    construction = fields.Char(string='Construction')
    knit_woven = fields.Selection([('knit', 'Knit'), ('woven', 'Woven')], string='Knit/Woven')
    color = fields.Char(string='Color')
    pantone = fields.Char(string='Pantone')
    finish = fields.Char(string='Finish')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    mill = fields.Char(string='Mill')
    country_of_origin_id = fields.Many2one('res.country', string='Country of Origin')

    # Consumption calculation
    net_consumption = fields.Float(string='Net Consumption (per piece)')
    cutting_wastage_pct = fields.Float(string='Cutting Loss %')
    shrinkage_wastage_pct = fields.Float(string='Shrinkage Loss %')
    marker_wastage_pct = fields.Float(string='Marker Loss %')
    process_wastage_pct = fields.Float(string='Process Loss %')
    shade_wastage_pct = fields.Float(string='Shade Loss %')
    quality_wastage_pct = fields.Float(string='Quality Loss %')
    total_wastage_pct = fields.Float(string='Total Wastage %', compute='_compute_consumption', store=True)
    gross_consumption = fields.Float(string='Gross Consumption (per piece)', compute='_compute_consumption', store=True)
    wastage_approved_by_id = fields.Many2one('res.users', string='Wastage Approved By')
    wastage_reason = fields.Text(string='Wastage Reason')

    uom = fields.Char(string='UoM', default='kg')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='bom_id.currency_id', store=True)
    required_qty = fields.Float(string='Total Required Qty', compute='_compute_consumption', store=True)
    line_cost = fields.Monetary(string='Line Cost', compute='_compute_consumption', store=True,
                                 currency_field='currency_id')

    # Bangladesh Garment Industry data (SRS section 36)
    yarn_count = fields.Char(string='Yarn Count')
    dye_lot = fields.Char(string='Dye Lot')
    shade_band = fields.Char(string='Shade Band')
    marker_efficiency_pct = fields.Float(string='Marker Efficiency %')
    wash_loss_pct = fields.Float(string='Wash Loss %')

    # Buyer requirements (SRS section 4.4 / 36)
    buyer_material_code = fields.Char(string='Buyer Material Code')
    buyer_description = fields.Char(string='Buyer Description')
    is_approved_mill = fields.Boolean(string='Approved Mill')
    is_restricted = fields.Boolean(string='Restricted Material')
    restriction_reason = fields.Char(string='Restriction Reason')

    # Compliance (SRS section 36)
    compliance_gots = fields.Boolean(string='GOTS')
    compliance_grs = fields.Boolean(string='GRS')
    compliance_oekotex = fields.Boolean(string='OEKO-TEX')
    compliance_rcs = fields.Boolean(string='RCS')
    compliance_higg_score = fields.Float(string='HIGG Index Score')
    compliance_chemical_status = fields.Selection([
        ('compliant', 'Compliant'), ('pending', 'Pending'), ('non_compliant', 'Non-Compliant'),
    ], string='Chemical Compliance', default='pending')

    # Purchase / Inventory integration (SRS section 23-24) — manually
    # entered pending real Warehouse/Purchase module integration; see
    # IMPLEMENTATION_NOTES.md.
    available_stock = fields.Float(string='Available Stock')
    reserved_stock = fields.Float(string='Reserved Stock')
    incoming_stock = fields.Float(string='Incoming Stock')
    safety_stock = fields.Float(string='Safety Stock')
    purchase_qty = fields.Float(string='Purchase Quantity', compute='_compute_purchase_qty', store=True)

    @api.depends('net_consumption', 'cutting_wastage_pct', 'shrinkage_wastage_pct', 'marker_wastage_pct',
                 'process_wastage_pct', 'shade_wastage_pct', 'quality_wastage_pct', 'unit_price',
                 'bom_id.order_quantity')
    def _compute_consumption(self):
        for rec in self:
            total_wastage = (rec.cutting_wastage_pct + rec.shrinkage_wastage_pct + rec.marker_wastage_pct
                              + rec.process_wastage_pct + rec.shade_wastage_pct + rec.quality_wastage_pct)
            rec.total_wastage_pct = total_wastage
            rec.gross_consumption = (rec.net_consumption or 0.0) * (1 + total_wastage / 100.0)
            order_qty = rec.bom_id.order_quantity or 0
            rec.required_qty = rec.gross_consumption * order_qty
            rec.line_cost = rec.required_qty * (rec.unit_price or 0.0)

    @api.depends('required_qty', 'available_stock', 'reserved_stock', 'incoming_stock', 'safety_stock')
    def _compute_purchase_qty(self):
        for rec in self:
            need = (rec.required_qty or 0.0) + (rec.safety_stock or 0.0) - (rec.available_stock or 0.0) \
                - (rec.incoming_stock or 0.0)
            rec.purchase_qty = max(need, 0.0)
