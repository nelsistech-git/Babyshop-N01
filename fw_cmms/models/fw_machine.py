# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwMachine(models.Model):
    _name = 'fw.machine'
    _description = 'Footwear Factory Machine Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Machine Name', required=True, tracking=True)
    code = fields.Char(string='Machine Code / Asset No.', required=True, tracking=True)
    machine_type = fields.Selection([
        ('cutting', 'Cutting Machine'),
        ('stitching', 'Stitching Machine'),
        ('lasting', 'Lasting / Assembly Machine'),
        ('finishing', 'Finishing / Packing Machine'),
        ('utility', 'Utility (Compressor, Boiler, Generator, etc.)'),
        ('other', 'Other'),
    ], string='Machine Type', required=True, default='other')

    factory_id = fields.Many2one('fw.factory', string='Factory', required=True, tracking=True)
    production_line_id = fields.Many2one('fw.production.line', string='Production Line',
                                          domain="[('factory_id', '=', factory_id)]")
    operation_id = fields.Many2one('fw.operation', string='Operation Performed')

    brand = fields.Char(string='Brand / Make')
    model_no = fields.Char(string='Model No.')
    serial_no = fields.Char(string='Serial No.')
    purchase_date = fields.Date(string='Purchase Date')
    warranty_end_date = fields.Date(string='Warranty End Date')

    responsible_technician_id = fields.Many2one('hr.employee', string='Responsible Technician')

    status = fields.Selection([
        ('running', 'Running'),
        ('idle', 'Idle'),
        ('under_maintenance', 'Under Maintenance'),
        ('breakdown', 'Breakdown'),
        ('scrapped', 'Scrapped'),
    ], string='Status', default='running', tracking=True)

    breakdown_ids = fields.One2many('fw.breakdown', 'machine_id', string='Breakdown History')
    breakdown_count = fields.Integer(string='Breakdown Count', compute='_compute_breakdown_count')
    pm_schedule_ids = fields.One2many('fw.pm.schedule', 'machine_id', string='PM Schedules')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Machine Code must be unique!'),
    ]

    def _compute_breakdown_count(self):
        for rec in self:
            rec.breakdown_count = len(rec.breakdown_ids)

    def name_get(self):
        result = []
        for rec in self:
            label = "[%s] %s" % (rec.code, rec.name) if rec.code else rec.name
            result.append((rec.id, label))
        return result

    def action_view_breakdowns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Breakdown History',
            'res_model': 'fw.breakdown',
            'view_mode': 'tree,form',
            'domain': [('machine_id', '=', self.id)],
            'context': {'default_machine_id': self.id},
        }
