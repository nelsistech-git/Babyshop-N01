# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentQualityCheckpoint(models.Model):
    """Quality Checkpoint — a reusable, stage-specific inspection checklist
    template covering the Cutting / Sewing / Finishing / Packing quality
    gates. See Quality Inspection Planning (base QMS SRS sec. 8) and Quality
    Checklist Management (Garment QMS SRS sec. 17)."""
    _name = 'garment.quality.checkpoint'
    _description = 'Garment Quality Checkpoint / Checklist Template'
    _order = 'sequence, id'

    name = fields.Char(string='Checkpoint Name', required=True)
    sequence = fields.Integer(default=10)
    stage = fields.Selection([
        ('incoming', 'Incoming Material'),
        ('fabric', 'Fabric Inspection'),
        ('accessory', 'Accessories Inspection'),
        ('cutting', 'Cutting QC'),
        ('sewing_inline', 'Sewing Inline QC'),
        ('endline', 'End Line QC'),
        ('washing', 'Washing QC'),
        ('finishing', 'Finishing QC'),
        ('final', 'Final Inspection / AQL'),
    ], string='Production Stage', required=True)
    style_id = fields.Many2one('garment.style', string='Style (leave empty for a generic template)')
    standard_id = fields.Many2one('garment.quality.standard', string='Quality Standard')
    line_ids = fields.One2many('garment.quality.checkpoint.line', 'checkpoint_id', string='Checklist Items')
    line_count = fields.Integer(compute='_compute_line_count')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)


class GarmentQualityCheckpointLine(models.Model):
    _name = 'garment.quality.checkpoint.line'
    _description = 'Garment Quality Checkpoint Checklist Item'
    _order = 'sequence, id'

    checkpoint_id = fields.Many2one('garment.quality.checkpoint', string='Checkpoint',
                                     required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    check_item = fields.Char(string='Check Item', required=True)
    is_mandatory = fields.Boolean(string='Mandatory', default=True)
    instructions = fields.Text(string='Instructions')
