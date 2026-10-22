# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentCadFile(models.Model):
    """CAD File Management + Marker Planning (SRS sections 20-21) — garment.cad.file."""
    _name = 'garment.cad.file'
    _description = 'Garment CAD File'
    _inherit = ['mail.thread']
    _order = 'cad_number desc'

    cad_number = fields.Char(string='CAD Number', copy=False, readonly=True, default=lambda s: _('New'))
    style_id = fields.Many2one('garment.style', string='Style', required=True, ondelete='cascade')
    pattern_id = fields.Many2one('garment.pattern', string='Pattern', domain="[('style_id', '=', style_id)]")
    pattern_version = fields.Char(string='Pattern Version')
    marker_version = fields.Char(string='Marker Version')
    marker_type = fields.Selection([
        ('single_size', 'Single Size Marker'), ('multi_size', 'Multi Size Marker'),
        ('single_color', 'Single Color Marker'), ('multi_color', 'Multi Color Marker'),
        ('tubular', 'Tubular Fabric Marker'), ('open_width', 'Open Width Marker'),
    ], string='Marker Type', default='single_size')

    marker_length = fields.Float(string='Marker Length (m)')
    marker_width = fields.Float(string='Marker Width (cm)')
    marker_efficiency = fields.Float(string='Marker Efficiency (%)')
    fabric_width = fields.Float(string='Fabric Width (cm)')
    total_consumption = fields.Float(string='Total Consumption')
    wastage_percent = fields.Float(string='Wastage %', compute='_compute_wastage', store=True)
    cost_impact = fields.Monetary(string='Cost Impact', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    cad_file = fields.Binary(string='CAD File', attachment=True, required=True)
    cad_filename = fields.Char(string='Filename')
    uploaded_by_id = fields.Many2one('res.users', string='Uploaded By', default=lambda s: s.env.user)
    upload_date = fields.Date(string='Upload Date', default=fields.Date.context_today)

    @api.depends('marker_efficiency')
    def _compute_wastage(self):
        for rec in self:
            rec.wastage_percent = max(0.0, 100.0 - (rec.marker_efficiency or 0.0))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('cad_number', _('New')) == _('New'):
                vals['cad_number'] = self.env['ir.sequence'].next_by_code('garment.cad.file') or _('New')
        return super().create(vals_list)
