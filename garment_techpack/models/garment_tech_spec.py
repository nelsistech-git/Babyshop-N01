# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentTechSpec(models.Model):
    """Technical Specification Sheet (SRS section 8) — garment.tech.spec."""
    _name = 'garment.tech.spec'
    _description = 'Garment Technical Specification'
    _order = 'sequence'

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    sewing_method = fields.Char(string='Sewing Method')
    stitch_type = fields.Char(string='Stitch Type')
    stitch_density = fields.Char(string='Stitch Density')
    seam_type = fields.Char(string='Seam Type')
    seam_allowance = fields.Char(string='Seam Allowance')
    thread_type = fields.Char(string='Thread Type')
    thread_count = fields.Char(string='Thread Count')
    spi = fields.Char(string='SPI (Stitch Per Inch)')
    needle_specification = fields.Char(string='Needle Specification')
    machine_requirement = fields.Char(string='Machine Requirement')
    notes = fields.Text(string='Notes')
