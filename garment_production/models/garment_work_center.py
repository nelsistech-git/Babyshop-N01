# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentWorkCenter(models.Model):
    """Work Center master — production stations (Cutting Table, Sewing Line,
    Washing Plant, Finishing Section, Packing Section, Printing/Embroidery
    Section...). See Production Management SRS s.13, MES SRS s.10, Planning &
    MES SRS s.15, Shop Floor SRS s.8."""
    _name = 'garment.work.center'
    _description = 'Garment Production Work Center'
    _order = 'sequence, name'

    name = fields.Char(string='Work Center Name', required=True)
    sequence = fields.Integer(default=10)
    code = fields.Char(string='Code')
    work_center_type = fields.Selection([
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('printing', 'Printing'),
        ('embroidery', 'Embroidery'), ('washing', 'Washing'), ('finishing', 'Finishing'),
        ('packing', 'Packing'), ('other', 'Other'),
    ], string='Work Center Type', required=True, default='sewing')
    department = fields.Selection([
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('washing', 'Washing'),
        ('finishing', 'Finishing'), ('packing', 'Packing'), ('control_room', 'Production Control Room'),
        ('planning', 'Planning'),
    ], string='Department')
    factory = fields.Char(string='Factory')
    floor = fields.Char(string='Floor')
    location = fields.Char(string='Location')
    supervisor_id = fields.Many2one('garment.hr.employee', string='Supervisor')
    capacity = fields.Float(string='Capacity (PCS/Day)')
    capacity_per_hour = fields.Float(string='Capacity (PCS/Hour)')
    machine_count = fields.Integer(string='Machine Count')
    operator_count = fields.Integer(string='Operator Count')
    working_hours = fields.Float(string='Working Hours/Day', default=8.0)
    status = fields.Selection([
        ('active', 'Active'), ('idle', 'Idle'), ('maintenance', 'Maintenance'), ('inactive', 'Inactive'),
    ], string='Status', default='active')
    machine_ids = fields.One2many('garment.production.machine', 'work_center_id', string='Machines')
    machine_ids_count = fields.Integer(compute='_compute_machine_count')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_machine_count(self):
        for rec in self:
            rec.machine_ids_count = len(rec.machine_ids)
