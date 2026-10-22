# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
PLM Cross-Functional Team Assignment (SRS section 11) — garment.plm.team.member.
"""
from odoo import fields, models


class GarmentPlmTeamMember(models.Model):
    _name = 'garment.plm.team.member'
    _description = 'Garment PLM Team Member'
    _order = 'project_id, role'

    project_id = fields.Many2one('garment.plm.project', string='PLM Project', required=True, ondelete='cascade')
    role = fields.Selection([
        ('merchandiser', 'Merchandiser'),
        ('designer', 'Designer'),
        ('pattern_maker', 'Pattern Maker'),
        ('sample_coordinator', 'Sample Coordinator'),
        ('ie_engineer', 'IE Engineer'),
        ('quality_team', 'Quality Team'),
        ('production_team', 'Production Team'),
    ], string='Role', required=True)
    employee_id = fields.Many2one('garment.hr.employee', string='Employee')
    user_id = fields.Many2one('res.users', string='Odoo User',
                               help='Optional link so this team member receives PLM notifications/activities.')
    is_lead = fields.Boolean(string='Team Lead')
    date_assigned = fields.Date(string='Assigned On', default=fields.Date.context_today)
    notes = fields.Char(string='Notes')
