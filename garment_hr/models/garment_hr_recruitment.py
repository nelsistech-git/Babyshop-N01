# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Recruitment Management + Manpower Requirement Planning (SRS sections
12-13) — garment.hr.recruitment.
"""
from odoo import api, fields, models, _


class GarmentHrRecruitment(models.Model):
    _name = 'garment.hr.recruitment'
    _description = 'Garment HR Recruitment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    requisition_number = fields.Char(string='Requisition Number', copy=False, readonly=True, default=lambda s: _('New'))
    department_id = fields.Many2one('garment.hr.department', string='Department', required=True)
    designation_id = fields.Many2one('garment.hr.designation', string='Designation', required=True)
    number_of_positions = fields.Integer(string='Number of Positions', default=1)
    request_date = fields.Date(string='Request Date', default=fields.Date.context_today)
    required_by_date = fields.Date(string='Required By')
    requested_by_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user)
    reason = fields.Selection([
        ('new_position', 'New Position'), ('replacement', 'Replacement'), ('expansion', 'Business Expansion'),
    ], string='Reason')

    candidate_ids = fields.One2many('garment.hr.candidate', 'recruitment_id', string='Candidates')
    candidate_count = fields.Integer(compute='_compute_candidate_count')

    status = fields.Selection([
        ('draft', 'Manpower Request'), ('approved', 'Approved'), ('sourcing', 'Sourcing'),
        ('interviewing', 'Interviewing'), ('offer', 'Offer Stage'), ('closed', 'Closed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_candidate_count(self):
        for rec in self:
            rec.candidate_count = len(rec.candidate_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('requisition_number', _('New')) == _('New'):
                vals['requisition_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.hr.recruitment') or _('New')
        return super().create(vals_list)
