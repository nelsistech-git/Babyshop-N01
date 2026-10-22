# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentOperatorAssignment(models.Model):
    """Operator Assignment — assigns an employee to an operation/machine on
    a line with a target and required skill level. See Production
    Management SRS s.31, Planning & MES SRS s.29 (Operator Allocation),
    MES SRS s.24."""
    _name = 'garment.operator.assignment'
    _description = 'Garment Operator Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, tracking=True)
    line_id = fields.Many2one('garment.production.line', string='Production Line', required=True, tracking=True)
    production_order_id = fields.Many2one('garment.production.order', string='Production Order')
    routing_line_id = fields.Many2one('garment.operation.routing.line', string='Operation')
    operation_name = fields.Char(string='Operation', required=True)
    machine_id = fields.Many2one('garment.production.machine', string='Machine')
    workstation = fields.Char(string='Workstation')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    shift = fields.Selection([
        ('morning', 'Morning'), ('evening', 'Evening'), ('night', 'Night'), ('general', 'General'),
    ], string='Shift', default='general')
    skill_level = fields.Selection([
        ('beginner', 'Beginner'), ('intermediate', 'Intermediate'),
        ('skilled', 'Skilled'), ('expert', 'Expert'), ('trainer', 'Trainer'),
    ], string='Skill Level')
    target_qty = fields.Float(string='Target (PCS/Day)')
    status = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
