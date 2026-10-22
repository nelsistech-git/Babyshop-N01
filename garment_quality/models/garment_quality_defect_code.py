# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentQualityDefectCode(models.Model):
    """Defect master / code library. See Quality Defect Database (base QMS
    SRS sec. 17), Defect Code Management (Garment QMS SRS sec. 16) and
    Defect Master Management (Advanced QMS SRS sec. 7)."""
    _name = 'garment.quality.defect.code'
    _description = 'Garment Quality Defect Code (Master)'
    _order = 'code'

    code = fields.Char(string='Defect Code', required=True)
    name = fields.Char(string='Defect Name', required=True)
    category = fields.Selection([
        ('incoming', 'Incoming Material'),
        ('fabric', 'Fabric'),
        ('accessory', 'Accessories / Trims'),
        ('cutting', 'Cutting'),
        ('sewing', 'Sewing'),
        ('washing', 'Washing'),
        ('finishing', 'Finishing'),
        ('packing', 'Packing'),
        ('other', 'Other'),
    ], string='Category', required=True)
    defect_group = fields.Selection([
        ('stitch', 'Stitch Defect'),
        ('assembly', 'Assembly Defect'),
        ('appearance', 'Appearance Defect'),
        ('measurement', 'Measurement Defect'),
        ('material', 'Material Defect'),
        ('other', 'Other'),
    ], string='Defect Group')
    severity = fields.Selection([
        ('critical', 'Critical'),
        ('major', 'Major'),
        ('minor', 'Minor'),
    ], string='Severity', required=True, default='minor')
    department = fields.Selection([
        ('incoming', 'Incoming / Warehouse'),
        ('cutting', 'Cutting'),
        ('sewing', 'Sewing'),
        ('washing', 'Washing'),
        ('finishing', 'Finishing'),
        ('packing', 'Packing'),
        ('quality', 'Quality'),
    ], string='Responsible Department')
    four_point_value = fields.Integer(
        string='4-Point System Value', default=1,
        help='Point value assigned for this defect under the 4-Point fabric inspection system '
             '(1 = small, 2 = medium, 3 = large, 4 = critical).')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('defect_code_uniq', 'unique(code)', 'A Defect Code must be unique!'),
    ]

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, '[%s] %s' % (rec.code, rec.name)))
        return result
