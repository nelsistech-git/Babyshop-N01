# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Candidate Management + Interview Management + Employee Joining Process
(SRS sections 15-17) — garment.hr.candidate.
"""
from odoo import fields, models


class GarmentHrCandidate(models.Model):
    _name = 'garment.hr.candidate'
    _description = 'Garment HR Candidate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'application_date desc'

    name = fields.Char(string='Candidate Name', required=True)
    recruitment_id = fields.Many2one('garment.hr.recruitment', string='Recruitment Requisition', required=True,
                                      ondelete='cascade')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    application_date = fields.Date(string='Application Date', default=fields.Date.context_today)
    resume = fields.Binary(string='Resume/CV', attachment=True)
    resume_filename = fields.Char(string='Filename')
    experience_years = fields.Integer(string='Experience (years)')
    referred_by = fields.Char(string='Referred By')

    interview_date = fields.Datetime(string='Interview Date')
    interviewer_id = fields.Many2one('res.users', string='Interviewer')
    interview_notes = fields.Text(string='Interview Notes')
    interview_score = fields.Float(string='Interview Score (%)')

    offered_salary = fields.Monetary(string='Offered Salary', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    joining_date = fields.Date(string='Joining Date')
    employee_id = fields.Many2one('garment.hr.employee', string='Resulting Employee', readonly=True, copy=False)

    status = fields.Selection([
        ('applied', 'Applied'), ('shortlisted', 'Shortlisted'), ('interview_scheduled', 'Interview Scheduled'),
        ('interviewed', 'Interviewed'), ('offered', 'Offered'), ('joined', 'Joined'), ('rejected', 'Rejected'),
    ], string='Status', default='applied', tracking=True)

    def action_convert_to_employee(self):
        self.ensure_one()
        employee = self.env['garment.hr.employee'].create({
            'name': self.name,
            'mobile': self.mobile,
            'department_id': self.recruitment_id.department_id.id,
            'designation_id': self.recruitment_id.designation_id.id,
            'joining_date': self.joining_date or fields.Date.context_today(self),
            'employment_type': 'probation',
        })
        self.write({'status': 'joined', 'employee_id': employee.id})
        return {
            'type': 'ir.actions.act_window', 'res_model': 'garment.hr.employee',
            'res_id': employee.id, 'view_mode': 'form',
        }
