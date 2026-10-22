# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Labor Compliance Record-Keeping (SRS section 51) — garment.hr.compliance.
Note: this is HR-side audit readiness record-keeping. Buyer-facing
compliance (BSCI/SEDEX/WRAP certificates) already lives on the Buyer
master (Module 1); this is a separate, factory-labor-law-focused record.
"""
from odoo import fields, models


class GarmentHrCompliance(models.Model):
    _name = 'garment.hr.compliance'
    _description = 'Garment HR Labor Compliance Record'
    _inherit = ['mail.thread']
    _order = 'audit_date desc'

    audit_date = fields.Date(string='Audit Date', default=fields.Date.context_today)
    compliance_type = fields.Selection([
        ('working_hours', 'Working Hours Compliance'), ('minimum_wage', 'Minimum Wage Compliance'),
        ('overtime_limit', 'Overtime Limit Compliance'), ('child_labor', 'Child Labor Check'),
        ('safety', 'Safety Compliance'), ('fire_safety', 'Fire Safety'), ('other', 'Other'),
    ], string='Compliance Type', required=True)
    department_id = fields.Many2one('garment.hr.department', string='Department')
    auditor_id = fields.Many2one('res.users', string='Auditor')
    finding = fields.Text(string='Finding')
    compliant = fields.Boolean(string='Compliant', default=True)
    corrective_action = fields.Text(string='Corrective Action')
    status = fields.Selection([
        ('open', 'Open'), ('in_progress', 'In Progress'), ('closed', 'Closed'),
    ], string='Status', default='open', tracking=True)

    def action_close(self):
        self.write({'status': 'closed'})
