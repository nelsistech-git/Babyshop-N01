# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Employee Complaint Management (HRM SRS section 52) — garment.hr.complaint.
Entirely missing from the original build. Workflow follows the SRS
exactly: Complaint Submit -> HR Review -> Investigation -> Resolution.
"""
from odoo import fields, models


class GarmentHrComplaint(models.Model):
    _name = 'garment.hr.complaint'
    _description = 'Garment Employee Complaint'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'submitted_date desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    category = fields.Selection([
        ('workplace', 'Workplace Issue'), ('salary', 'Salary Issue'), ('supervisor', 'Supervisor Issue'),
        ('safety', 'Safety Issue'), ('welfare', 'Welfare Issue'),
    ], string='Category', required=True)
    submitted_date = fields.Date(string='Submitted Date', default=fields.Date.context_today)
    description = fields.Text(string='Description', required=True)
    assigned_to_id = fields.Many2one('res.users', string='Assigned To')
    investigation_notes = fields.Text(string='Investigation Notes')
    resolution_notes = fields.Text(string='Resolution')

    status = fields.Selection([
        ('submitted', 'Submitted'), ('hr_review', 'HR Review'), ('investigation', 'Investigation'),
        ('resolved', 'Resolved'), ('closed', 'Closed'),
    ], string='Status', default='submitted', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def action_start_review(self):
        self.write({'status': 'hr_review'})

    def action_start_investigation(self):
        self.write({'status': 'investigation'})

    def action_resolve(self):
        self.write({'status': 'resolved'})

    def action_close(self):
        self.write({'status': 'closed'})
