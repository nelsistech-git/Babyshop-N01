# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Training Management + Training Schedule + Training Evaluation (SRS
sections 43-45) — garment.hr.training.
"""
from odoo import fields, models


class GarmentHrTraining(models.Model):
    _name = 'garment.hr.training'
    _description = 'Garment Employee Training'
    _inherit = ['mail.thread']
    _order = 'scheduled_date desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    training_name = fields.Char(string='Training Name', required=True)
    training_type = fields.Selection([
        ('skill_development', 'Skill Development'), ('safety', 'Safety Training'),
        ('compliance', 'Compliance Training'), ('machine_operation', 'Machine Operation'),
        ('quality', 'Quality Training'), ('orientation', 'New Joiner Orientation'),
    ], string='Training Type', required=True)
    trainer = fields.Char(string='Trainer')
    scheduled_date = fields.Date(string='Scheduled Date')
    duration_hours = fields.Float(string='Duration (hours)')
    status = fields.Selection([
        ('scheduled', 'Scheduled'), ('ongoing', 'Ongoing'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled', tracking=True)
    evaluation_score = fields.Float(string='Evaluation Score (%)')
    evaluation_notes = fields.Text(string='Evaluation Notes')

    def action_mark_completed(self):
        self.write({'status': 'completed'})
