# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentStyleColor(models.Model):
    """Colorway management (SRS section 12) — garment.style.color."""
    _name = 'garment.style.color'
    _description = 'Garment Style Colorway'
    _order = 'sequence'

    style_id = fields.Many2one('garment.style', string='Style', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    colorway_code = fields.Char(string='Colorway Code')
    colorway_name = fields.Char(string='Colorway Name', required=True)
    pantone_number = fields.Char(string='Pantone Number')
    buyer_color_name = fields.Char(string='Buyer Color Name')
    factory_color_name = fields.Char(string='Factory Color Name')
    fabric_color = fields.Char(string='Fabric Color')
    trim_color = fields.Char(string='Trim Color')
    thread_color = fields.Char(string='Thread Color')
    print_color = fields.Char(string='Print Color')
    embroidery_color = fields.Char(string='Embroidery Color')
    packaging_color = fields.Char(string='Packaging Color')

    front_view_image = fields.Binary(string='Front View', attachment=True)
    back_view_image = fields.Binary(string='Back View', attachment=True)
    close_up_image = fields.Binary(string='Close-up View', attachment=True)
    fabric_swatch_image = fields.Binary(string='Fabric Swatch', attachment=True)
    trim_swatch_image = fields.Binary(string='Trim Swatch', attachment=True)
    packaging_preview_image = fields.Binary(string='Packaging Preview', attachment=True)

    status = fields.Selection([
        ('draft', 'Draft'), ('under_review', 'Under Review'), ('buyer_approval', 'Buyer Approval'),
        ('approved', 'Approved'), ('discontinued', 'Discontinued'),
    ], string='Colorway Status', default='draft')
