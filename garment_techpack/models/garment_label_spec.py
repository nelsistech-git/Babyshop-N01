# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentLabelSpec(models.Model):
    """Label Specification (SRS section 13) — garment.label.spec."""
    _name = 'garment.label.spec'
    _description = 'Garment Label Specification'
    _order = 'sequence'

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    label_type = fields.Selection([
        ('main', 'Main Label'), ('size', 'Size Label'), ('care', 'Care Label'), ('brand', 'Brand Label'),
        ('composition', 'Composition Label'), ('security', 'Security Label'), ('rfid', 'RFID Label'),
    ], string='Label Type', required=True)
    label_code = fields.Char(string='Label Code')
    material = fields.Char(string='Material')
    size = fields.Char(string='Size')
    color = fields.Char(string='Color')
    position = fields.Char(string='Position')
    sewing_method = fields.Char(string='Sewing Method')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    label_image = fields.Binary(string='Label Image', attachment=True)
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft')
