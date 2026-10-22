# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Technician Management (Maintenance & Asset Mgmt SRS sec. 5, CMMS SRS
sec. 5 & 17). Both source SRS documents list a separate "Technician"
model (``garment.maintenance.technician`` / entries in the department
structure). The maintenance workforce is not re-modeled here — this
file EXTENDS the existing ``garment.hr.employee`` (garment_hr) in place
with the handful of maintenance-specific fields the SRS asks for
(specialization, certification, technician flag) so Technician stays a
single real employee record shared with HR/Payroll/Attendance instead
of a second, disconnected person record. See IMPLEMENTATION_NOTES.md.
"""
from odoo import fields, models


class GarmentHrEmployeeMaintenanceExtension(models.Model):
    _inherit = 'garment.hr.employee'

    is_maintenance_technician = fields.Boolean(
        string='Maintenance Technician',
        help='Check to make this employee selectable as a technician/engineer on Maintenance Work Orders.')
    maintenance_specialization = fields.Selection([
        ('mechanical', 'Mechanical'),
        ('electrical', 'Electrical'),
        ('electronic', 'Electronic / Instrumentation'),
        ('general', 'General / Multi-skilled'),
    ], string='Maintenance Specialization')
    maintenance_certification = fields.Char(string='Maintenance Certification')
    maintenance_experience_years = fields.Float(string='Maintenance Experience (Years)')
    maintenance_workorder_ids = fields.One2many(
        'garment.maintenance.workorder', 'technician_id', string='Assigned Work Orders')
    maintenance_workorder_count = fields.Integer(compute='_compute_maintenance_workorder_count')

    def _compute_maintenance_workorder_count(self):
        for rec in self:
            rec.maintenance_workorder_count = len(rec.maintenance_workorder_ids)

    def action_view_maintenance_workorders(self):
        self.ensure_one()
        return {
            'name': 'Maintenance Work Orders', 'type': 'ir.actions.act_window',
            'res_model': 'garment.maintenance.workorder', 'view_mode': 'tree,form',
            'domain': [('technician_id', '=', self.id)],
            'context': {'default_technician_id': self.id},
        }
