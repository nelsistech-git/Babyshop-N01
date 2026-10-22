# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Fire Safety Management System (SRS1 secs. 29-32, SRS2 secs. 31-37) —
garment.compliance.fire.equipment / garment.compliance.fire.drill.
"""
from odoo import api, fields, models


class GarmentComplianceFireEquipment(models.Model):
    _name = 'garment.compliance.fire.equipment'
    _description = 'Garment Fire Equipment'
    _inherit = ['mail.thread']
    _order = 'next_inspection_date'

    name = fields.Char(string='Equipment ID', required=True)
    equipment_type = fields.Selection([
        ('extinguisher', 'Fire Extinguisher'), ('alarm', 'Fire Alarm'), ('pump', 'Fire Pump'),
        ('hose', 'Fire Hose'), ('sprinkler', 'Sprinkler System'), ('emergency_lighting', 'Emergency Lighting'),
        ('emergency_exit', 'Emergency Exit'),
    ], string='Equipment Type', required=True)
    location_id = fields.Many2one('garment.location', string='Location')
    location_text = fields.Char(string='Location (Free Text)', help='Use when no warehouse location applies, e.g. "Sewing Floor - 3rd Floor".')
    installation_date = fields.Date(string='Installation Date')
    last_inspection_date = fields.Date(string='Last Inspection Date')
    next_inspection_date = fields.Date(string='Next Inspection Date')
    expiry_date = fields.Date(string='Expiry Date')
    accessible = fields.Boolean(string='Accessible / Clear', default=True)
    status = fields.Selection([
        ('active', 'Active'), ('needs_service', 'Needs Service'), ('expired', 'Expired'), ('out_of_service', 'Out of Service'),
    ], string='Status', compute='_compute_status', store=True, readonly=False, tracking=True, default='active')

    responsible_user_id = fields.Many2one('res.users', string='Responsible Person')

    @api.depends('expiry_date', 'next_inspection_date')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.expiry_date and rec.expiry_date < today:
                rec.status = 'expired'
            elif rec.next_inspection_date and rec.next_inspection_date < today:
                rec.status = 'needs_service'
            # else: leave the current value (default 'active', or a manually
            # set 'out_of_service') untouched rather than overwriting it.


class GarmentComplianceFireDrill(models.Model):
    _name = 'garment.compliance.fire.drill'
    _description = 'Garment Fire Drill'
    _inherit = ['mail.thread']
    _order = 'drill_date desc'

    name = fields.Char(string='Drill Name', required=True, default='Fire Drill')
    drill_date = fields.Date(string='Drill Date', default=fields.Date.context_today)
    department_id = fields.Many2one('garment.hr.department', string='Department')
    participant_count = fields.Integer(string='Participants')
    evacuation_time_minutes = fields.Float(string='Evacuation Time (Minutes)')
    result = fields.Selection([
        ('passed', 'Passed'), ('needs_improvement', 'Needs Improvement'), ('failed', 'Failed'),
    ], string='Result', default='passed', tracking=True)
    findings = fields.Text(string='Findings')
    improvement_plan = fields.Text(string='Improvement Plan')
    status = fields.Selection([
        ('scheduled', 'Scheduled'), ('completed', 'Completed'), ('evaluated', 'Performance Evaluated'),
    ], string='Status', default='scheduled', tracking=True)
