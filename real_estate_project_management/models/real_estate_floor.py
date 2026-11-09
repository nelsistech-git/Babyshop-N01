# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateFloor(models.Model):
    _name = 'real.estate.floor'
    _description = 'Real Estate Floor'
    _rec_name = 'floor_name'
    _order = 'building_id, floor_number'

    name = fields.Char(string='Floor Code', copy=False)
    floor_name = fields.Char(string='Floor Name', required=True,
                              help='e.g. "Ground Floor", "Floor 10"')
    floor_number = fields.Integer(string='Floor Number', required=True,
                                   help='Use 0 for Ground Floor, negative for basements.')

    building_id = fields.Many2one('real.estate.building', string='Building',
                                   required=True, ondelete='cascade')
    block_id = fields.Many2one('real.estate.block', string='Block',
                                domain="[('building_id', '=', building_id)]",
                                ondelete='set null')
    project_id = fields.Many2one(related='building_id.project_id', store=True, readonly=True)
    company_id = fields.Many2one(related='building_id.company_id', store=True, readonly=True)

    unit_ids = fields.One2many('real.estate.unit', 'floor_id', string='Units')
    unit_count = fields.Integer(compute='_compute_unit_count')

    _sql_constraints = [
        ('floor_building_uniq', 'unique(floor_number, building_id, block_id)',
         'This floor number already exists for this building/block.'),
    ]

    @api.depends('unit_ids')
    def _compute_unit_count(self):
        for rec in self:
            rec.unit_count = len(rec.unit_ids)

    @api.onchange('building_id')
    def _onchange_building_id(self):
        if self.block_id and self.block_id.building_id != self.building_id:
            self.block_id = False

    def action_view_units(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Units',
            'res_model': 'real.estate.unit',
            'view_mode': 'kanban,tree,form',
            'domain': [('floor_id', '=', self.id)],
            'context': {'default_floor_id': self.id},
        }
