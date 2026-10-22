# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Workstation Management (SRS s.31) — sewing workstation setup: machine,
table position, tools/attachments and assigned operator."""
from odoo import fields, models

from .garment_ie_operation import MACHINE_TYPE_SELECTION


class GarmentIeWorkstation(models.Model):
    _name = 'garment.ie.workstation'
    _description = 'Garment IE Workstation'
    _order = 'line_id, code'
    _rec_name = 'code'

    code = fields.Char(string='Station Code', required=True, copy=False, help='e.g. Line-05-OP-10')
    line_id = fields.Many2one('garment.production.line', string='Production Line')
    operation_id = fields.Many2one('garment.ie.operation', string='Operation')
    machine_type = fields.Selection(MACHINE_TYPE_SELECTION, string='Machine Type')
    employee_id = fields.Many2one('garment.hr.employee', string='Assigned Operator')
    table_position = fields.Char(string='Table Position')
    tools = fields.Char(string='Tools')
    attachments = fields.Char(string='Attachments')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', 'Station Code must be unique per company!'),
    ]
