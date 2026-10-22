# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
PLM Task Management (SRS section 47) — garment.plm.task.
"""
from odoo import fields, models


class GarmentPlmTask(models.Model):
    _name = 'garment.plm.task'
    _description = 'Garment PLM Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, id'

    project_id = fields.Many2one('garment.plm.project', string='PLM Project', required=True, ondelete='cascade')
    style_id = fields.Many2one(related='project_id.style_id', string='Style', store=True, readonly=True)
    stage_gate_id = fields.Many2one('garment.plm.stage.gate', string='Stage Gate',
                                     domain="[('project_id', '=', project_id)]")

    name = fields.Char(string='Task', required=True)
    task_type = fields.Selection([
        ('create_techpack', 'Create Tech Pack'),
        ('prepare_sample', 'Prepare Sample'),
        ('update_bom', 'Update BOM'),
        ('submit_approval', 'Submit Approval'),
        ('complete_revision', 'Complete Revision'),
        ('other', 'Other'),
    ], string='Task Type', default='other')

    assigned_to_id = fields.Many2one('res.users', string='Assigned To', tracking=True)
    due_date = fields.Date(string='Due Date', tracking=True)
    completed_date = fields.Date(string='Completed Date', copy=False)
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', related='project_id.company_id', store=True, readonly=True)

    def action_start(self):
        self.write({'status': 'running'})

    def action_complete(self):
        self.write({'status': 'completed', 'completed_date': fields.Date.context_today(self)})
