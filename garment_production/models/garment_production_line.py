# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentProductionLine(models.Model):
    """Production Line master (mainly Sewing, but generalized for any
    department). See Production Management SRS s.29, Planning & MES SRS
    s.18/22, MES SRS s.15, Shop Floor SRS s.7."""
    _name = 'garment.production.line'
    _description = 'Garment Production Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'line_number'
    _rec_name = 'line_number'

    line_number = fields.Char(string='Line Number', required=True, tracking=True)
    name = fields.Char(string='Line Name')
    department = fields.Selection([
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('washing', 'Washing'),
        ('finishing', 'Finishing'), ('packing', 'Packing'),
    ], string='Department', required=True, default='sewing', tracking=True)
    factory = fields.Char(string='Factory')
    floor = fields.Char(string='Floor')
    supervisor_id = fields.Many2one('garment.hr.employee', string='Supervisor', tracking=True)
    line_leader_id = fields.Many2one('garment.hr.employee', string='Line Leader')
    operator_count = fields.Integer(string='Operator Count')
    machine_count = fields.Integer(string='Machine Count')
    working_hours = fields.Float(string='Working Hours/Day', default=8.0)
    capacity_per_day = fields.Float(string='Daily Capacity (PCS)')
    efficiency_target_pct = fields.Float(string='Target Efficiency (%)', default=70.0)

    current_style_id = fields.Many2one('garment.style', string='Current Style')
    current_order_id = fields.Many2one('garment.production.order', string='Current Production Order')
    hourly_target = fields.Float(string='Hourly Target (PCS)')
    daily_target = fields.Float(string='Daily Target (PCS)')

    status = fields.Selection([
        ('running', 'Running'), ('idle', 'Idle'), ('breakdown', 'Breakdown'),
        ('maintenance', 'Maintenance'), ('offline', 'Offline'),
    ], string='Status', default='idle', tracking=True)
    andon_status = fields.Selection([
        ('green', 'Running'), ('yellow', 'Warning'), ('red', 'Problem'),
    ], string='Andon Status', default='green', tracking=True)

    machine_ids = fields.One2many('garment.production.machine', 'line_id', string='Machines')
    entry_ids = fields.One2many('garment.production.entry', 'line_id', string='Production Entries')
    downtime_ids = fields.One2many('garment.machine.downtime', 'line_id', string='Downtime Records')
    entry_count = fields.Integer(compute='_compute_counts')
    downtime_count = fields.Integer(compute='_compute_counts')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('line_number_uniq', 'unique(line_number, company_id)', 'Line Number must be unique per company!'),
    ]

    def _compute_counts(self):
        for rec in self:
            rec.entry_count = len(rec.entry_ids)
            rec.downtime_count = len(rec.downtime_ids)

    def action_view_entries(self):
        self.ensure_one()
        return {
            'name': 'Production Entries', 'type': 'ir.actions.act_window', 'res_model': 'garment.production.entry',
            'view_mode': 'tree,form', 'domain': [('line_id', '=', self.id)],
            'context': {'default_line_id': self.id},
        }
