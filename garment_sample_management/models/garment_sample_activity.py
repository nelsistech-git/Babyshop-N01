# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentSampleActivity(models.Model):
    """Sample Development Plan activities (SRS section 9) + Sample Room
    tracking (SRS section 12) — garment.sample.activity."""
    _name = 'garment.sample.activity'
    _description = 'Garment Sample Development Activity'
    _order = 'sequence'

    sample_id = fields.Many2one('garment.sample', string='Sample', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    activity_type = fields.Selection([
        ('pattern_preparation', 'Pattern Preparation'), ('fabric_allocation', 'Fabric Allocation'),
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('printing', 'Printing'), ('embroidery', 'Embroidery'),
        ('washing', 'Washing'), ('finishing', 'Finishing'), ('packing', 'Packing'),
        ('inspection', 'Inspection'), ('submission', 'Submission'),
    ], string='Activity', required=True)
    responsible_person_id = fields.Many2one('res.users', string='Responsible Person')
    sample_room = fields.Char(string='Sample Room')
    machine = fields.Char(string='Machine')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    status = fields.Selection([
        ('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('delayed', 'Delayed'),
    ], string='Status', default='pending')
    progress = fields.Float(string='Progress %', default=0.0)

    # Sample Production Tracking (SRS section 14) — shown/used contextually per activity_type.
    # Cutting
    cutter_id = fields.Many2one('res.users', string='Cutter')
    fabric_used = fields.Char(string='Fabric Used')
    panel_status = fields.Selection([
        ('pending', 'Pending'), ('cut', 'Cut'), ('checked', 'Checked'),
    ], string='Panel Status')
    # Sewing
    sewing_start = fields.Datetime(string='Sewing Start')
    sewing_complete = fields.Datetime(string='Sewing Complete')
    # Finishing
    ironing_done = fields.Boolean(string='Ironing Done')
    trimming_done = fields.Boolean(string='Trimming Done')
    packing_done = fields.Boolean(string='Packing Done')

    def action_mark_completed(self):
        self.write({'status': 'completed', 'progress': 100.0})
