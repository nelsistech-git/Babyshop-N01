# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Skill Matrix Management + Operation Skill Mapping (SRS sections 41-42)
— garment.hr.skill.matrix.
"""
from odoo import fields, models


class GarmentHrSkillMatrix(models.Model):
    _name = 'garment.hr.skill.matrix'
    _description = 'Garment Employee Skill Matrix'
    _order = 'employee_id'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    operation = fields.Selection([
        ('cutting', 'Cutting'), ('sewing_overlock', 'Sewing - Overlock'), ('sewing_flatlock', 'Sewing - Flatlock'),
        ('sewing_single_needle', 'Sewing - Single Needle'), ('button_hole', 'Button Hole'),
        ('embroidery', 'Embroidery'), ('printing', 'Printing'), ('washing', 'Washing'),
        ('ironing', 'Ironing'), ('quality_check', 'Quality Check'), ('packing', 'Packing'),
    ], string='Operation', required=True)
    proficiency_level = fields.Selection([
        ('1', '1 - Beginner'), ('2', '2 - Basic'), ('3', '3 - Competent'), ('4', '4 - Proficient'), ('5', '5 - Expert'),
    ], string='Proficiency Level', default='1')
    certified_date = fields.Date(string='Certified Date')
    last_assessed_date = fields.Date(string='Last Assessed Date')
