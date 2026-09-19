# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwBomSizeGrading(models.Model):
    _name = 'fw.bom.size.grading'
    _description = 'Footwear BOM Component Size-Wise Consumption'
    _order = 'bom_line_id, size_id'

    bom_line_id = fields.Many2one('fw.bom.line', string='BOM Component Line', required=True,
                                   ondelete='cascade')
    size_id = fields.Many2one('fw.size', string='Size', required=True)
    qty_per_pair = fields.Float(string='Qty per Pair (this Size)',
                                 digits='Product Unit of Measure', required=True, default=0.0)
    remarks = fields.Char(string='Remarks')

    _sql_constraints = [
        ('bom_line_size_uniq', 'unique(bom_line_id, size_id)',
         'This size already has a consumption grading row for this BOM component!'),
    ]

    @api.constrains('qty_per_pair')
    def _check_qty_non_negative(self):
        for rec in self:
            if rec.qty_per_pair < 0:
                raise ValidationError("Qty per Pair (this Size) cannot be negative.")
