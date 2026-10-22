# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Corrective Action Management / CAPA (SRS1 secs. 13-14, SRS2 secs. 45-46)
— garment.compliance.capa. Factory-level compliance CAPA — distinct from
garment_supplier.garment.supplier.capa (supplier-caused issues) and
garment_quality.garment.quality.capa (production/quality-process
issues). Can originate from a compliance Finding, a Safety Incident, or
be self-identified.
"""
from odoo import api, fields, models, _


class GarmentComplianceCapa(models.Model):
    _name = 'garment.compliance.capa'
    _description = 'Garment Compliance CAPA (Corrective And Preventive Action)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date'

    capa_no = fields.Char(string='CAPA No.', copy=False, readonly=True, default=lambda s: _('New'))
    source = fields.Selection([
        ('audit_finding', 'Audit Finding'), ('incident', 'Safety Incident'),
        ('inspection', 'Inspection'), ('buyer_requirement', 'Buyer Requirement'), ('self_identified', 'Self-Identified'),
    ], string='Source', default='audit_finding', required=True)
    finding_id = fields.Many2one('garment.compliance.finding', string='Related Finding')
    audit_id = fields.Many2one('garment.compliance.audit', string='Related Audit')
    incident_id = fields.Many2one('garment.compliance.incident', string='Related Incident')
    department_id = fields.Many2one('garment.hr.department', string='Department')

    issue = fields.Text(string='Issue / Problem Description', required=True)
    root_cause_method = fields.Selection([
        ('5why', '5 Why Analysis'), ('fishbone', 'Fishbone Analysis'), ('risk_assessment', 'Risk Assessment'), ('other', 'Other'),
    ], string='Root Cause Method')
    root_cause = fields.Text(string='Root Cause')
    corrective_action = fields.Text(string='Corrective Action')
    preventive_action = fields.Text(string='Preventive Action')
    responsible_user_id = fields.Many2one('res.users', string='Responsible Person')
    due_date = fields.Date(string='Due Date')
    implementation_date = fields.Date(string='Implementation Date')
    verification_date = fields.Date(string='Verification Date')
    verified_by_id = fields.Many2one('res.users', string='Verified By')
    verification_result = fields.Selection([
        ('effective', 'Effective'), ('not_effective', 'Not Effective'),
    ], string='Verification Result')
    status = fields.Selection([
        ('open', 'Open'), ('root_cause', 'Root Cause Analysis'), ('action_planned', 'Corrective Action Plan'),
        ('in_progress', 'Implementation'), ('verification', 'Verification'), ('closed', 'Closed'),
    ], string='Status', default='open', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('capa_no', _('New')) == _('New'):
                vals['capa_no'] = self.env['ir.sequence'].next_by_code('garment.compliance.capa') or _('New')
        return super().create(vals_list)

    def action_close(self):
        self.write({'status': 'closed'})
