# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentTechpackTask(models.Model):
    """Tech Pack Task Management (SRS section 26) — garment.techpack.task."""
    _name = 'garment.techpack.task'
    _description = 'Garment Tech Pack Task'
    _order = 'due_date'

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    name = fields.Char(string='Task Name', required=True)
    assigned_to_id = fields.Many2one('res.users', string='Assigned Person')
    department = fields.Selection([
        ('technical', 'Technical'), ('sampling', 'Sampling'), ('production', 'Production'),
    ], string='Department', required=True)
    due_date = fields.Date(string='Due Date')
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1')
    status = fields.Selection([
        ('todo', 'To Do'), ('in_progress', 'In Progress'), ('done', 'Done'), ('cancelled', 'Cancelled'),
    ], string='Status', default='todo')
    completion_percent = fields.Float(string='Completion %', default=0.0)

    def action_mark_done(self):
        self.write({'status': 'done', 'completion_percent': 100.0})
