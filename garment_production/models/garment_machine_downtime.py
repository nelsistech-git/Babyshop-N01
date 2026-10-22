# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentMachineDowntime(models.Model):
    """Machine / line downtime with reason-code capture. See Planning & MES
    SRS s.33-34, MES SRS s.18, Shop Floor SRS s.30 (Production Downtime
    Management)."""
    _name = 'garment.machine.downtime'
    _description = 'Garment Machine Downtime'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'

    machine_id = fields.Many2one('garment.production.machine', string='Machine')
    line_id = fields.Many2one('garment.production.line', string='Production Line', required=True, tracking=True)
    work_center_id = fields.Many2one('garment.work.center', string='Work Center')
    production_order_id = fields.Many2one('garment.production.order', string='Production Order')

    start_datetime = fields.Datetime(string='Start Time', required=True, default=fields.Datetime.now)
    end_datetime = fields.Datetime(string='End Time')
    duration_minutes = fields.Float(string='Duration (Minutes)', compute='_compute_duration', store=True)

    reason = fields.Selection([
        ('machine_failure', 'Machine Failure'), ('material_shortage', 'Material Shortage'),
        ('operator_issue', 'Operator Issue'), ('no_operator', 'No Operator'),
        ('power_problem', 'Power Problem'), ('quality_issue', 'Quality Issue'),
        ('quality_hold', 'Quality Hold'), ('planning_issue', 'Planning Issue'), ('other', 'Other'),
    ], string='Downtime Reason', required=True, tracking=True)
    reported_by_id = fields.Many2one('res.users', string='Reported By', default=lambda s: s.env.user)
    action_taken = fields.Text(string='Action Taken')
    production_loss_qty = fields.Float(string='Production Loss (PCS)')

    status = fields.Selection([
        ('open', 'Open'), ('resolved', 'Resolved'),
    ], string='Status', default='open', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                rec.duration_minutes = (rec.end_datetime - rec.start_datetime).total_seconds() / 60.0
            else:
                rec.duration_minutes = 0.0

    def action_resolve(self):
        self.write({'status': 'resolved', 'end_datetime': self.end_datetime or fields.Datetime.now()})
