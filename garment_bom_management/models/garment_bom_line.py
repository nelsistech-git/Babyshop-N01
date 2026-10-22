# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentBomLine(models.Model):
    """Generic BOM Material Line (SRS section 8) — garment.bom.line.
    Covers any material category at a basic level; Fabric/Trim/Packaging
    BOM models extend this with category-specific fields. This is the
    consolidated list kept in sync (garment.bom.action_sync_material_lines)
    from Fabric/Trim/Packaging BOM, and is the model garment_production
    reads for Material Issue / Consumption tracking (MODEL_MAP)."""
    _name = 'garment.bom.line'
    _description = 'Garment BOM Material Line'
    _order = 'sequence'

    bom_id = fields.Many2one('garment.bom', string='BOM', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Line Number', default=10)
    material_category = fields.Selection([
        ('fabric', 'Fabric'), ('trim', 'Trim'), ('packaging', 'Packaging'), ('other', 'Other'),
    ], string='Material Category', required=True)
    material_code = fields.Char(string='Material Code')
    material_name = fields.Char(string='Material Name', required=True)
    description = fields.Char(string='Description')
    specification = fields.Char(string='Specification')
    uom = fields.Char(string='UoM')
    required_qty = fields.Float(string='Required Quantity')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='bom_id.currency_id', store=True)
    line_cost = fields.Monetary(string='Line Cost', compute='_compute_line_cost', store=True,
                                 currency_field='currency_id')
    supplier_id = fields.Many2one('res.partner', string='Supplier')

    # Bangladesh / Buyer requirements (SRS section 36)
    buyer_material_code = fields.Char(string='Buyer Material Code')
    is_restricted = fields.Boolean(string='Restricted Material')
    restriction_reason = fields.Char(string='Restriction Reason')

    # Production-floor read fields (SRS section 4.5 Production Floor BOM)
    issued_qty = fields.Float(string='Issue Quantity', help='Quantity issued to the production floor so far.')
    consumed_qty = fields.Float(string='Consumption', help='Quantity actually consumed on the production floor.')

    # Traceability back to the category-specific line this was generated from.
    source_ref = fields.Reference(selection=[
        ('garment.fabric.bom', 'Fabric BOM'),
        ('garment.trim.bom', 'Trim BOM'),
        ('garment.packaging.bom', 'Packaging BOM'),
    ], string='Source Line')

    def _compute_line_cost(self):
        for rec in self:
            rec.line_cost = (rec.required_qty or 0.0) * (rec.unit_price or 0.0)
