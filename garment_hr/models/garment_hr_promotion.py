# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Promotion & Increment Management (SRS section 48) + Employee Transfer
Management (Module 36 SRS section 18: Department Transfer / Line Transfer
/ Position Change) — garment.hr.promotion. Transfer is folded into this
model, since it already carried a 'transfer' promotion_type option that
previously did nothing on approval.
"""
from odoo import fields, models


class GarmentHrPromotion(models.Model):
    _name = 'garment.hr.promotion'
    _description = 'Garment Employee Promotion'
    _inherit = ['mail.thread']
    _order = 'effective_date desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    promotion_type = fields.Selection([
        ('promotion', 'Promotion'), ('increment', 'Salary Increment'), ('transfer', 'Department Transfer'),
    ], string='Type', required=True)
    previous_designation_id = fields.Many2one('garment.hr.designation', string='Previous Designation')
    new_designation_id = fields.Many2one('garment.hr.designation', string='New Designation')
    previous_department_id = fields.Many2one('garment.hr.department', string='Previous Department')
    new_department_id = fields.Many2one('garment.hr.department', string='New Department')
    previous_line_assignment = fields.Char(string='Previous Line')
    new_line_assignment = fields.Char(string='New Line')
    previous_salary = fields.Monetary(string='Previous Salary', currency_field='currency_id')
    new_salary = fields.Monetary(string='New Salary', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    effective_date = fields.Date(string='Effective Date', default=fields.Date.context_today)
    reason = fields.Text(string='Reason')
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    def action_approve(self):
        self.write({'status': 'approved', 'approved_by_id': self.env.user.id})
        for rec in self:
            vals = {}
            if rec.new_designation_id:
                vals['designation_id'] = rec.new_designation_id.id
            if rec.new_department_id:
                vals['department_id'] = rec.new_department_id.id
            if rec.new_line_assignment:
                vals['line_assignment'] = rec.new_line_assignment
            if vals:
                rec.employee_id.write(vals)
