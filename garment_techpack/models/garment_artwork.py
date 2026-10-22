# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

# Supported Files (SRS section 10)
ARTWORK_SUPPORTED_EXTENSIONS = ('.ai', '.psd', '.pdf', '.png', '.jpg', '.jpeg', '.svg', '.eps')


class GarmentArtwork(models.Model):
    """Artwork Management + Print/Embroidery Specification
    (SRS sections 10-12) — garment.artwork."""
    _name = 'garment.artwork'
    _description = 'Garment Artwork'
    _inherit = ['mail.thread']
    _order = 'artwork_number desc'

    artwork_number = fields.Char(string='Artwork Number', copy=False, readonly=True, default=lambda s: _('New'))
    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    style_id = fields.Many2one('garment.style', string='Style', related='techpack_id.style_id', store=True)
    artwork_type = fields.Selection([
        ('print', 'Print Artwork'), ('embroidery', 'Embroidery Artwork'), ('heat_transfer', 'Heat Transfer Artwork'),
        ('logo', 'Logo Artwork'), ('label', 'Label Artwork'), ('packaging', 'Packaging Artwork'),
    ], string='Artwork Type', required=True)
    placement = fields.Char(string='Placement')
    size = fields.Char(string='Size')
    color = fields.Char(string='Color')
    pantone = fields.Char(string='Pantone')
    technique = fields.Char(string='Technique')

    # Print-specific (SRS section 11)
    print_type = fields.Char(string='Print Type', help='e.g. Placement Print, All-Over Print, Panel Print.')
    print_method = fields.Selection([
        ('screen_print', 'Screen Print'), ('digital_print', 'Digital Print'), ('sublimation', 'Sublimation'),
        ('heat_transfer', 'Heat Transfer'), ('rubber_print', 'Rubber Print'), ('silicone_print', 'Silicone Print'),
        ('foil_print', 'Foil Print'), ('puff_print', 'Puff Print'),
    ], string='Print Method')
    print_location = fields.Char(string='Print Location')
    printing_sequence = fields.Char(string='Printing Sequence')
    print_supplier_id = fields.Many2one('res.partner', string='Print Supplier')
    testing_requirement = fields.Char(string='Testing Requirement')

    # Embroidery-specific (SRS section 12)
    embroidery_type = fields.Char(string='Embroidery Type', help='e.g. Flat Embroidery, Applique, Chenille, 3D Puff.')
    embroidery_thread_color = fields.Char(string='Embroidery Thread Color')
    embroidery_thread_brand = fields.Char(string='Embroidery Thread Brand')
    stitch_count = fields.Char(string='Stitch Count')
    embroidery_machine_type = fields.Char(string='Embroidery Machine Type')
    backing_requirement = fields.Char(string='Backing Requirement')

    file_version = fields.Char(string='File Version', default='1.0')
    artwork_file = fields.Binary(string='Artwork File', attachment=True)
    artwork_filename = fields.Char(string='Filename')
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('artwork_number', _('New')) == _('New'):
                vals['artwork_number'] = self.env['ir.sequence'].next_by_code('garment.artwork') or _('New')
        return super().create(vals_list)

    @api.constrains('artwork_filename')
    def _check_artwork_filename(self):
        """Supported Files (SRS section 10): AI, PSD, PDF, PNG, JPG, SVG, EPS."""
        for rec in self:
            if rec.artwork_filename and '.' in rec.artwork_filename:
                ext = '.' + rec.artwork_filename.rsplit('.', 1)[-1].lower()
                if ext not in ARTWORK_SUPPORTED_EXTENSIONS:
                    raise ValidationError(_(
                        'Unsupported artwork file type "%s". Supported formats: AI, PSD, PDF, PNG, JPG, SVG, EPS.'
                    ) % ext)
