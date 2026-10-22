# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentMeasurementPoint(models.Model):
    """Reusable Measurement Point master (SRS section 17 Measurement Chart
    Management + section 35 Menu Structure > Configuration > Measurement
    Points). Standardizes point codes/descriptions/measurement method across
    every measurement chart instead of free-typing them per chart line."""
    _name = 'garment.measurement.point'
    _description = 'Garment Measurement Point (Master)'
    _order = 'sequence, point_code'

    point_code = fields.Char(string='Point Code', required=True)
    name = fields.Char(string='Description', required=True,
                        help='e.g. Chest Width, Waist Width, Hip Width, Shoulder Width, Sleeve Length, '
                             'Body Length, Neck Width, Neck Depth, Armhole, Bottom Opening, Cuff Width, '
                             'Pocket Position, Pocket Size, Hood Height, Hood Width, Collar Height, Collar Length')
    sequence = fields.Integer(default=10)
    product_category_id = fields.Many2one('garment.style.category', string='Product Category',
                                            help='Leave blank to make this point available to all categories.')
    default_measurement_method = fields.Char(string='Measurement Method',
                                               help='How this point is physically measured, e.g. '
                                                    '"Lay flat, seam to seam, 1 inch below armhole".')
    illustration_reference = fields.Binary(string='Illustration Reference', attachment=True)
    illustration_filename = fields.Char(string='Illustration Filename')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('point_code_uniq', 'unique(point_code)', 'A measurement point with this code already exists!'),
    ]
