# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
BI Dashboard (SRS sections 8, 10, 14-19, 40, 45) — garment.dashboard.board.

A Board is a named, role-visible collection of Tiles (garment.dashboard.tile).
It renders as a plain Odoo kanban-of-tiles view — see
views/garment_dashboard_board_views.xml and
views/garment_dashboard_tile_views.xml — no OWL widget involved. Seed boards
for Executive / Factory / Quality / Finance dashboards are in
data/garment_dashboard_board_data.xml.
"""
from odoo import api, fields, models, _

from .garment_kpi_definition import CATEGORY_SELECTION


class GarmentDashboardBoard(models.Model):
    _name = 'garment.dashboard.board'
    _description = 'Garment BI Dashboard Board'
    _order = 'sequence, name'

    name = fields.Char(string='Dashboard Name', required=True)
    category = fields.Selection(CATEGORY_SELECTION, string='Category', default='executive')
    description = fields.Text(string='Description')
    sequence = fields.Integer(default=10)

    owner_id = fields.Many2one('res.users', string='Owner', default=lambda s: s.env.user)
    visible_group_ids = fields.Many2many(
        'res.groups', string='Visible To Groups',
        help='Role-based dashboard visibility (SRS section 39). Leave empty to leave visibility to '
             'standard model access rights only.')

    tile_ids = fields.One2many('garment.dashboard.tile', 'board_id', string='Tiles')
    tile_count = fields.Integer(string='Tile Count', compute='_compute_tile_count')

    is_default = fields.Boolean(string='Default Dashboard')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('tile_ids')
    def _compute_tile_count(self):
        for rec in self:
            rec.tile_count = len(rec.tile_ids)

    def action_view_tiles(self):
        self.ensure_one()
        return {
            'name': self.name, 'type': 'ir.actions.act_window', 'res_model': 'garment.dashboard.tile',
            'view_mode': 'kanban,tree,form', 'domain': [('board_id', '=', self.id)],
            'context': {'default_board_id': self.id},
        }

    def action_add_tile(self):
        self.ensure_one()
        return {
            'name': _('New Tile'), 'type': 'ir.actions.act_window', 'res_model': 'garment.dashboard.tile',
            'view_mode': 'form', 'target': 'new', 'context': {'default_board_id': self.id},
        }
