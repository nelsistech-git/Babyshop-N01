# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Accident & Incident Management (SRS1 sec. 33) — garment.compliance.incident.
Workplace injury/accident/fire/safety-violation reporting feeding into
CAPA, part of the Health & Safety Management System (SRS1 sec. 26).
"""
from odoo import api, fields, models, _


class GarmentComplianceIncident(models.Model):
    _name = 'garment.compliance.incident'
    _description = 'Garment Compliance Safety Incident'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'incident_date desc'

    incident_no = fields.Char(string='Incident No.', copy=False, readonly=True, default=lambda s: _('New'))
    incident_type = fields.Selection([
        ('injury', 'Injury'), ('machine_accident', 'Machine Accident'),
        ('fire_incident', 'Fire Incident'), ('safety_violation', 'Safety Violation'), ('near_miss', 'Near Miss'),
    ], string='Incident Type', required=True, tracking=True)
    incident_date = fields.Datetime(string='Incident Date/Time', default=fields.Datetime.now)
    department_id = fields.Many2one('garment.hr.department', string='Department')
    employee_id = fields.Many2one('garment.hr.employee', string='Employee Involved')
    location_id = fields.Many2one('garment.location', string='Location')
    reported_by_id = fields.Many2one('res.users', string='Reported By', default=lambda s: s.env.user)
    description = fields.Text(string='Description', required=True)
    severity = fields.Selection([
        ('minor', 'Minor'), ('major', 'Major'), ('critical', 'Critical'),
    ], string='Severity', default='minor', tracking=True)
    investigation_findings = fields.Text(string='Investigation Findings')
    root_cause = fields.Text(string='Root Cause')
    capa_ids = fields.One2many('garment.compliance.capa', 'incident_id', string='Corrective Actions')
    capa_count = fields.Integer(compute='_compute_capa_count')
    status = fields.Selection([
        ('reported', 'Reported'), ('investigating', 'Investigation'),
        ('corrective_action', 'Corrective Action'), ('closed', 'Closed'),
    ], string='Status', default='reported', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_capa_count(self):
        for rec in self:
            rec.capa_count = len(rec.capa_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('incident_no', _('New')) == _('New'):
                vals['incident_no'] = self.env['ir.sequence'].next_by_code('garment.compliance.incident') or _('New')
        return super().create(vals_list)

    def action_close(self):
        self.write({'status': 'closed'})
