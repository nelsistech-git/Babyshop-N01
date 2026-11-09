# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateBlock(models.Model):
    """Optional sub-division of a Building (e.g. Tower A / Tower B)."""
    _name = 'real.estate.block'
    _description = 'Real Estate Block'
    _rec_name = 'block_name'
    _order = 'building_id, sequence, id'

    name = fields.Char(string='Block Code', copy=False)
    block_name = fields.Char(string='Block Name', required=True)
    sequence = fields.Integer(default=10)

    building_id = fields.Many2one('real.estate.building', string='Building',
                                   required=True, ondelete='cascade')
    project_id = fields.Many2one(related='building_id.project_id', store=True, readonly=True)
    company_id = fields.Many2one(related='building_id.company_id', store=True, readonly=True)

    floor_ids = fields.One2many('real.estate.floor', 'block_id', string='Floors')
    floor_count = fields.Integer(compute='_compute_counts')
    unit_ids = fields.One2many('real.estate.unit', 'block_id', string='Units')
    unit_count = fields.Integer(compute='_compute_counts')

    _sql_constraints = [
        ('name_building_uniq', 'unique(name, building_id)',
         'Block Code must be unique within a building.'),
    ]

    @api.depends('floor_ids', 'unit_ids')
    def _compute_counts(self):
        for rec in self:
            rec.floor_count = len(rec.floor_ids)
            rec.unit_count = len(rec.unit_ids)
