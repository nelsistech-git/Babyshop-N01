# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentSupplierCategory(models.Model):
    """Supplier Category Management (SRS section 11) —
    garment.supplier.category."""
    _name = 'garment.supplier.category'
    _description = 'Garment Supplier Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    group = fields.Selection([
        ('material', 'Material Supplier'), ('service', 'Service Supplier'), ('logistics', 'Logistics Supplier'),
        ('compliance', 'Compliance Supplier'),
    ], string='Category Group', required=True)
    sub_type = fields.Selection([
        ('fabric', 'Fabric'), ('yarn', 'Yarn'), ('trim', 'Trims'), ('packaging', 'Packaging'),
        ('washing', 'Washing'), ('printing', 'Printing'), ('embroidery', 'Embroidery'),
        ('freight', 'Freight'), ('transport', 'Transport'),
        ('testing_lab', 'Testing Laboratory'), ('certification_provider', 'Certification Provider'),
        ('inspection_agency', 'Inspection Agency'), ('other', 'Other'),
    ], string='Sub Type')
    active = fields.Boolean(default=True)
