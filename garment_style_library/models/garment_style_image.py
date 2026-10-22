# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentStyleImage(models.Model):
    """Structured image gallery (SRS section 13) — garment.style.image."""
    _name = 'garment.style.image'
    _description = 'Garment Style Image'
    _order = 'sequence'

    style_id = fields.Many2one('garment.style', string='Style', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    image_category = fields.Selection([
        ('front', 'Front View'), ('back', 'Back View'), ('left', 'Left View'), ('right', 'Right View'),
        ('top', 'Top View'), ('bottom', 'Bottom View'), ('close_up', 'Close-up'), ('label', 'Label Placement'),
        ('pocket', 'Pocket Detail'), ('collar', 'Collar Detail'), ('sleeve', 'Sleeve Detail'), ('packaging', 'Packaging Image'),
    ], string='Image Category', required=True)
    image = fields.Binary(string='Image', attachment=True, required=True)
    image_filename = fields.Char(string='Filename')
    image_version = fields.Char(string='Version', default='1.0')
    uploaded_by_id = fields.Many2one('res.users', string='Uploaded By', default=lambda s: s.env.user)
    upload_date = fields.Date(string='Upload Date', default=fields.Date.context_today)
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft')
    notes = fields.Char(string='Image Notes')
