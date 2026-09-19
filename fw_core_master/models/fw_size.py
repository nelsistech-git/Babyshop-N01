# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwSize(models.Model):
    _name = 'fw.size'
    _description = 'Footwear Size Master'
    _order = 'sequence, size_value'

    name = fields.Char(string='Size Label', required=True, help="E.g. 39, 40, 7US, 6UK")
    size_value = fields.Float(string='Numeric Value', required=True,
                               help="Numeric sort key, e.g. 39.0")
    size_system = fields.Selection([
        ('eu', 'EU'),
        ('us', 'US'),
        ('uk', 'UK'),
        ('cm', 'CM / Mondopoint'),
    ], string='Size System', default='eu', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_system_uniq', 'unique(name, size_system)',
         'This size label already exists for the selected size system!'),
    ]


class FwSizeCurve(models.Model):
    _name = 'fw.size.curve'
    _description = 'Footwear Size Curve (Size Run)'
    _order = 'name'

    name = fields.Char(string='Size Curve Name', required=True,
                        help="E.g. EU 36-45 Men Standard Run")
    size_system = fields.Selection([
        ('eu', 'EU'),
        ('us', 'US'),
        ('uk', 'UK'),
        ('cm', 'CM / Mondopoint'),
    ], string='Size System', default='eu', required=True)
    line_ids = fields.One2many('fw.size.curve.line', 'curve_id', string='Sizes in Curve')
    total_ratio = fields.Integer(string='Total Ratio', compute='_compute_total_ratio')
    active = fields.Boolean(default=True)

    @api.depends('line_ids.ratio')
    def _compute_total_ratio(self):
        for rec in self:
            rec.total_ratio = sum(rec.line_ids.mapped('ratio'))


class FwSizeCurveLine(models.Model):
    _name = 'fw.size.curve.line'
    _description = 'Footwear Size Curve Line'
    _order = 'size_id'

    curve_id = fields.Many2one('fw.size.curve', string='Size Curve',
                                required=True, ondelete='cascade')
    size_id = fields.Many2one('fw.size', string='Size', required=True)
    ratio = fields.Integer(string='Ratio (per set)', default=1,
                            help="Number of pairs of this size per size-set, "
                                 "e.g. 1:2:2:2:1 curve")

    _sql_constraints = [
        ('curve_size_uniq', 'unique(curve_id, size_id)',
         'This size already exists in the selected size curve!'),
    ]

    @api.constrains('ratio')
    def _check_ratio(self):
        for rec in self:
            if rec.ratio < 0:
                raise ValidationError("Size curve ratio cannot be negative.")
