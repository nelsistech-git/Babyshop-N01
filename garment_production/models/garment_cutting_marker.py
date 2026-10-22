# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentCuttingMarker(models.Model):
    """Marker Management — marker planning and efficiency calculation.
    Formula: Marker Efficiency = Used Area / Total Fabric Area x 100.
    See Production Management SRS s.24."""
    _name = 'garment.cutting.marker'
    _description = 'Garment Cutting Marker'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Marker Number', copy=False, readonly=True, default=lambda s: _('New'))
    style_id = fields.Many2one('garment.style', string='Style', required=True)
    size_ratio = fields.Char(string='Size Ratio', help='e.g. S:1 M:2 L:2 XL:1')
    marker_length = fields.Float(string='Marker Length (m)')
    fabric_width = fields.Float(string='Fabric Width (inch)')
    ply_count = fields.Integer(string='Ply Count')
    cad_file_id = fields.Many2one('garment.cad.file', string='CAD File Reference')

    used_area = fields.Float(string='Used Area (sq.m)')
    total_fabric_area = fields.Float(string='Total Fabric Area (sq.m)')
    efficiency_pct = fields.Float(string='Marker Efficiency (%)', compute='_compute_efficiency', store=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('used_area', 'total_fabric_area')
    def _compute_efficiency(self):
        for rec in self:
            rec.efficiency_pct = (rec.used_area / rec.total_fabric_area * 100.0) if rec.total_fabric_area else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.cutting.marker') or _('New')
        return super().create(vals_list)
