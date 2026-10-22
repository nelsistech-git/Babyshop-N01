# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Compliance Requirement / Checklist Management (SRS1 sec. 8, SRS2 secs.
6-7, 12) — garment.compliance.requirement. Department-wise checklist
items and buyer/regulatory requirements, reused both as a standalone
requirement register and as the source of Audit checklist lines.
"""
from odoo import fields, models


class GarmentComplianceRequirement(models.Model):
    _name = 'garment.compliance.requirement'
    _description = 'Garment Compliance Requirement / Checklist Item'
    _order = 'category, sequence, name'

    name = fields.Char(string='Requirement Name', required=True)
    sequence = fields.Integer(default=10)
    standard_id = fields.Many2one('garment.compliance.standard', string='Standard')
    category = fields.Selection([
        ('hr', 'HR Compliance'),
        ('safety', 'Safety Compliance'),
        ('fire', 'Fire Safety Compliance'),
        ('factory', 'Factory / Building Compliance'),
        ('environmental', 'Environmental Compliance'),
        ('government', 'Government Compliance'),
        ('other', 'Other'),
    ], string='Category', required=True, default='hr')
    description = fields.Text(string='Description')
    applicable_department_id = fields.Many2one('garment.hr.department', string='Applicable Department')
    required_frequency = fields.Selection([
        ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'), ('half_yearly', 'Half-Yearly'), ('annual', 'Annual'),
        ('one_time', 'One-Time'),
    ], string='Required Frequency', default='annual')
    priority = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], string='Priority', default='medium')
    responsible_user_id = fields.Many2one('res.users', string='Responsible Person')
    status = fields.Selection([
        ('active', 'Active'), ('inactive', 'Inactive'),
    ], string='Status', default='active')
    active = fields.Boolean(default=True)
