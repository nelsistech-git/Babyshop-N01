# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentHrDepartment(models.Model):
    """Department Management (SRS section 9) — garment.hr.department."""
    _name = 'garment.hr.department'
    _description = 'Garment HR Department'
    _order = 'name'

    name = fields.Char(required=True)
    factory = fields.Char(string='Factory')
    manager_id = fields.Many2one('garment.hr.employee', string='Department Manager')
    parent_id = fields.Many2one('garment.hr.department', string='Parent Department')
    employee_ids = fields.One2many('garment.hr.employee', 'department_id', string='Employees')
    employee_count = fields.Integer(string='Employee Count', compute='_compute_employee_count')
    active = fields.Boolean(default=True)

    def _compute_employee_count(self):
        for rec in self:
            rec.employee_count = len(rec.employee_ids)
