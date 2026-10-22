# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentSampleMaterial(models.Model):
    """Sample Material Planning + Reservation (SRS sections 10-11) —
    garment.sample.material."""
    _name = 'garment.sample.material'
    _description = 'Garment Sample Material Reservation'
    _order = 'sequence'

    sample_id = fields.Many2one('garment.sample', string='Sample', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    material_type = fields.Selection([
        ('fabric', 'Fabric'), ('thread', 'Thread'), ('button', 'Button'), ('zipper', 'Zipper'),
        ('label', 'Label'), ('packaging', 'Packaging'), ('trim', 'Other Trim'),
    ], string='Material Type', required=True)
    description = fields.Char(string='Description')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    uom = fields.Char(string='UoM')
    required_qty = fields.Float(string='Required Quantity')
    available_qty = fields.Float(string='Available Quantity')
    reserved_qty = fields.Float(string='Reserved Quantity')
    issued_qty = fields.Float(string='Issued Quantity')
    shortage_qty = fields.Float(string='Shortage', compute='_compute_shortage', store=True)

    @api.depends('required_qty', 'available_qty')
    def _compute_shortage(self):
        for rec in self:
            rec.shortage_qty = max(0.0, (rec.required_qty or 0.0) - (rec.available_qty or 0.0))
