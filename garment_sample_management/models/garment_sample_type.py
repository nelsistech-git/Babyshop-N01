# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentSampleType(models.Model):
    """Sample Types (SRS section 7) — garment.sample.type."""
    _name = 'garment.sample.type'
    _description = 'Garment Sample Type'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    code = fields.Selection([
        ('proto', 'Proto Sample'), ('fit', 'Fit Sample'), ('size_set', 'Size Set Sample'),
        ('pp', 'PP (Pre-Production) Sample'), ('salesman', 'Salesman Sample'), ('shipment', 'Shipment Sample'),
        # Bangladesh Woven/Sweater process extensions (SRS section 45)
        ('development', 'Development Sample'), ('sealed', 'Sealed Sample'),
        ('yarn_approval', 'Yarn Approval'), ('color_approval', 'Color Approval'),
        ('knitting', 'Knitting Sample'), ('linking', 'Linking Sample'), ('wash', 'Wash Sample'),
    ], string='Sample Category', required=True)
    purpose = fields.Text(string='Purpose')
    active = fields.Boolean(default=True)
