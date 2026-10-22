# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentConstructionDetail(models.Model):
    """Garment Construction Details (SRS section 9) — garment.construction.detail.
    Covers body, sleeve, collar, pocket and closure construction as flexible
    component lines so any garment type can be described consistently."""
    _name = 'garment.construction.detail'
    _description = 'Garment Construction Detail'
    _order = 'sequence'

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    component = fields.Selection([
        ('front_panel', 'Front Panel'), ('back_panel', 'Back Panel'), ('side_seam', 'Side Seam'),
        ('shoulder', 'Shoulder Construction'), ('armhole', 'Armhole Construction'), ('hem', 'Hem Construction'),
        ('sleeve', 'Sleeve'), ('cuff', 'Cuff'), ('collar', 'Collar'), ('pocket', 'Pocket'), ('closure', 'Closure'),
    ], string='Component', required=True)
    construction_notes = fields.Text(string='Construction Details')

    # Sleeve-specific
    sleeve_attachment = fields.Char(string='Sleeve Attachment')
    sleeve_opening = fields.Char(string='Sleeve Opening')
    sleeve_measurement = fields.Char(string='Sleeve Measurement')

    # Collar-specific
    collar_height = fields.Char(string='Collar Height')
    collar_width = fields.Char(string='Collar Width')
    collar_interlining = fields.Char(string='Collar Interlining')
    collar_stitching = fields.Char(string='Collar Stitching')

    # Pocket-specific
    pocket_position = fields.Char(string='Pocket Position')
    pocket_size = fields.Char(string='Pocket Size')
    pocket_shape = fields.Char(string='Pocket Shape')
    pocket_opening = fields.Char(string='Pocket Opening')
    pocket_stitching = fields.Char(string='Pocket Stitching')

    # Closure-specific
    closure_type = fields.Selection([
        ('zipper', 'Zipper'), ('button', 'Button'), ('snap', 'Snap'),
        ('velcro', 'Velcro'), ('hook', 'Hook'), ('eyelet', 'Eyelet'),
    ], string='Closure Type')
    closure_size = fields.Char(string='Closure Size')
    closure_brand = fields.Char(string='Closure Brand')
    closure_color = fields.Char(string='Closure Color')
    closure_placement = fields.Char(string='Closure Placement')
