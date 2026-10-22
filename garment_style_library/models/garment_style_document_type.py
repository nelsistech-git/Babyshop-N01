# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentStyleDocumentType(models.Model):
    """Configurable Document Types master (SRS section 14 Digital Asset
    Management + section 35 Menu Structure > Configuration > Document Types).
    Lets Product Development standardize the supported file formats per
    asset category instead of hard-coding them."""
    _name = 'garment.style.document.type'
    _description = 'Garment Style Document Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, help='e.g. Buyer Tech Pack (PDF), DXF Pattern File, 3D Garment Asset (GLB)')
    sequence = fields.Integer(default=10)
    category = fields.Selection([
        ('document', 'Document'), ('image', 'Image'), ('cad', 'CAD'),
        ('3d_asset', '3D Asset'), ('video', 'Video'),
    ], string='Category', required=True, default='document')
    allowed_extensions = fields.Char(
        string='Allowed File Extensions',
        help='Comma separated, e.g. "pdf,docx,xlsx,txt" or "dxf,plt,ai,pdf,zip"')
    active = fields.Boolean(default=True)
