# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwWorkerSkill(models.Model):
    _name = 'fw.worker.skill'
    _description = 'Footwear Worker Skill Matrix Entry'
    _order = 'employee_id, operation_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    operation_id = fields.Many2one('fw.operation', string='Operation', required=True)
    skill_level = fields.Selection([
        ('trainee', 'Trainee'),
        ('semi_skilled', 'Semi-Skilled'),
        ('skilled', 'Skilled'),
        ('expert', 'Expert'),
    ], string='Skill Level', required=True, default='trainee')

    certified_date = fields.Date(string='Certified Date')
    certified_by = fields.Many2one('res.users', string='Certified By')
    remarks = fields.Char(string='Remarks')

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('employee_operation_uniq', 'unique(employee_id, operation_id)',
         'A skill entry already exists for this employee and operation. '
         'Please edit the existing entry instead.'),
    ]
