# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Discipline & Warning Management (SRS section 49) — garment.hr.discipline.
"""
from odoo import fields, models


class GarmentHrDiscipline(models.Model):
    _name = 'garment.hr.discipline'
    _description = 'Garment Employee Disciplinary Record'
    _inherit = ['mail.thread']
    _order = 'incident_date desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    incident_date = fields.Date(string='Incident Date', default=fields.Date.context_today)
    issue_type = fields.Selection([
        ('attendance', 'Attendance Issue'), ('misconduct', 'Misconduct'), ('quality_issue', 'Quality Issue'),
        ('safety_violation', 'Safety Violation'), ('insubordination', 'Insubordination'), ('other', 'Other'),
    ], string='Issue Type', required=True)
    description = fields.Text(string='Description')
    action_taken = fields.Selection([
        ('verbal_warning', 'Verbal Warning'), ('written_warning', 'Written Warning'),
        ('suspension', 'Suspension'), ('termination', 'Termination'), ('none', 'No Action'),
    ], string='Action Taken', default='verbal_warning')
    issued_by_id = fields.Many2one('res.users', string='Issued By', default=lambda s: s.env.user)
    status = fields.Selection([
        ('open', 'Open'), ('resolved', 'Resolved'), ('escalated', 'Escalated'),
    ], string='Status', default='open', tracking=True)

    def action_resolve(self):
        self.write({'status': 'resolved'})
