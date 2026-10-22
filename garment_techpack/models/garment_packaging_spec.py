# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentPackagingSpec(models.Model):
    """Packaging Specification (SRS section 14) — garment.packaging.spec."""
    _name = 'garment.packaging.spec'
    _description = 'Garment Packaging Specification'
    _order = 'sequence'

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    poly_bag_type = fields.Char(string='Poly Bag Type')
    poly_bag_size = fields.Char(string='Poly Bag Size')
    thickness = fields.Char(string='Thickness')
    carton_type = fields.Char(string='Carton Type')
    carton_dimension = fields.Char(string='Carton Dimension')
    carton_marking = fields.Text(string='Carton Marking')
    folding_method = fields.Char(string='Folding Method')
    hanger_requirement = fields.Boolean(string='Hanger Requirement')
    tissue_requirement = fields.Boolean(string='Tissue Requirement')
    barcode_requirement = fields.Boolean(string='Barcode Requirement')
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft')
