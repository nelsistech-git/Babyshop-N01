# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateBuilding(models.Model):
    _name = 'real.estate.building'
    _description = 'Real Estate Building'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'building_name'
    _order = 'project_id, sequence, id'

    name = fields.Char(string='Building Code', copy=False, tracking=True)
    building_name = fields.Char(string='Building Name', required=True, tracking=True)
    sequence = fields.Integer(default=10)

    project_id = fields.Many2one('real.estate.project', string='Project',
                                  required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)

    total_floors = fields.Integer(string='Total Floors')
    building_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('mixed', 'Mixed Use'),
        ('parking', 'Parking'),
        ('amenity', 'Amenity Block'),
    ], string='Building Type', default='residential')

    block_ids = fields.One2many('real.estate.block', 'building_id', string='Blocks')
    block_count = fields.Integer(compute='_compute_counts')
    floor_ids = fields.One2many('real.estate.floor', 'building_id', string='Floors')
    floor_count = fields.Integer(compute='_compute_counts')
    unit_ids = fields.One2many('real.estate.unit', 'building_id', string='Units')
    unit_count = fields.Integer(compute='_compute_counts')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_project_uniq', 'unique(name, project_id)',
         'Building Code must be unique within a project.'),
    ]

    @api.depends('block_ids', 'floor_ids', 'unit_ids')
    def _compute_counts(self):
        for rec in self:
            rec.block_count = len(rec.block_ids)
            rec.floor_count = len(rec.floor_ids)
            rec.unit_count = len(rec.unit_ids)

    def action_view_floors(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Floors',
            'res_model': 'real.estate.floor',
            'view_mode': 'tree,form',
            'domain': [('building_id', '=', self.id)],
            'context': {'default_building_id': self.id},
        }

    def action_view_units(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Units',
            'res_model': 'real.estate.unit',
            'view_mode': 'kanban,tree,form',
            'domain': [('building_id', '=', self.id)],
            'context': {'default_building_id': self.id},
        }
