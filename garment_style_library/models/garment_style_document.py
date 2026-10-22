# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentStyleDocument(models.Model):
    """Digital Asset Management (SRS section 14) — garment.style.document."""
    _name = 'garment.style.document'
    _description = 'Garment Style Digital Asset'
    _order = 'sequence'

    style_id = fields.Many2one('garment.style', string='Style', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Asset Name', required=True)
    asset_category = fields.Selection([
        ('document', 'Document'), ('image', 'Image'), ('cad', 'CAD'), ('3d_asset', '3D Asset'), ('video', 'Video'),
    ], string='Category', required=True)
    file = fields.Binary(string='File', attachment=True, required=True)
    filename = fields.Char(string='Filename')
    version = fields.Char(string='Version', default='1.0')
    document_type_id = fields.Many2one('garment.style.document.type', string='Document Type')
    tag_ids = fields.Many2many('garment.style.document.tag', string='Tags')
    thumbnail = fields.Binary(string='Preview Thumbnail', attachment=True,
                               help='Small preview image shown in list/gallery views, independent of the '
                                    'full asset file (SRS section 14).')
    download_permission = fields.Selection([
        ('all', 'All Users'), ('internal', 'Internal Only'), ('restricted', 'Restricted'),
    ], string='Download Permission', default='internal')
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft')
