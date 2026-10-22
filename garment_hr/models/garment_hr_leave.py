# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Leave Management + Application Workflow + Balance Management (SRS
sections 26-28). Not in the SRS's own two DB model tables, but too
central to the workforce workflow to omit — added pragmatically as
garment.hr.leave, matching how other modules added well-justified models
beyond a source SRS's own explicit list.
"""
from odoo import api, fields, models


class GarmentHrLeave(models.Model):
    _name = 'garment.hr.leave'
    _description = 'Garment Employee Leave'
    _inherit = ['mail.thread']
    _order = 'start_date desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    leave_type = fields.Selection([
        ('casual', 'Casual Leave'), ('sick', 'Sick Leave'), ('earned', 'Earned Leave'),
        ('maternity', 'Maternity Leave'), ('unpaid', 'Unpaid Leave'), ('festival', 'Festival Holiday'),
    ], string='Leave Type', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    days = fields.Integer(string='Number of Days', compute='_compute_days', store=True)
    reason = fields.Text(string='Reason')

    approver_id = fields.Many2one('res.users', string='Approver')
    status = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('line_manager_review', 'Line Manager Review'),
        ('hr_approval', 'HR Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('start_date', 'end_date')
    def _compute_days(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date >= rec.start_date:
                rec.days = (rec.end_date - rec.start_date).days + 1
            else:
                rec.days = 0

    def action_submit(self):
        self.write({'status': 'submitted'})

    def action_approve(self):
        self.write({'status': 'approved', 'approver_id': self.env.user.id})

    def action_reject(self):
        self.write({'status': 'rejected', 'approver_id': self.env.user.id})
