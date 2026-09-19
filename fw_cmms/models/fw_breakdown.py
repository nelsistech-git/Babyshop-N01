# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwBreakdown(models.Model):
    _name = 'fw.breakdown'
    _description = 'Footwear Machine Breakdown (Corrective Maintenance)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reported_date desc'

    name = fields.Char(string='Breakdown Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.breakdown') or 'New')
    machine_id = fields.Many2one('fw.machine', string='Machine', required=True, tracking=True)
    factory_id = fields.Many2one(related='machine_id.factory_id', string='Factory', store=True)

    reported_by = fields.Many2one('res.users', string='Reported By',
                                   default=lambda self: self.env.user)
    reported_date = fields.Datetime(string='Reported On', default=fields.Datetime.now)

    breakdown_reason = fields.Selection([
        ('mechanical', 'Mechanical'),
        ('electrical', 'Electrical'),
        ('electronic', 'Electronic'),
        ('operator_error', 'Operator Error'),
        ('other', 'Other'),
    ], string='Breakdown Reason', default='mechanical')
    description = fields.Text(string='Problem Description')

    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Priority', default='medium', tracking=True)

    state = fields.Selection([
        ('reported', 'Reported'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='reported', tracking=True)

    assigned_technician_id = fields.Many2one('hr.employee', string='Assigned Technician',
                                              tracking=True)
    start_repair_datetime = fields.Datetime(string='Repair Start')
    end_repair_datetime = fields.Datetime(string='Repair End')
    downtime_hours = fields.Float(string='Downtime (Hours)', compute='_compute_downtime',
                                   store=True)

    spare_used_ids = fields.One2many('fw.breakdown.spare.line', 'breakdown_id',
                                      string='Spare Parts Used')
    resolution_notes = fields.Text(string='Resolution Notes')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.breakdown') or 'New'
        return super().create(vals_list)

    @api.depends('start_repair_datetime', 'end_repair_datetime')
    def _compute_downtime(self):
        for rec in self:
            if rec.start_repair_datetime and rec.end_repair_datetime:
                delta = rec.end_repair_datetime - rec.start_repair_datetime
                rec.downtime_hours = delta.total_seconds() / 3600.0
            else:
                rec.downtime_hours = 0.0

    def action_assign(self):
        self.write({'state': 'assigned'})

    def action_start_repair(self):
        self.write({'state': 'in_progress', 'start_repair_datetime': fields.Datetime.now()})
        self.mapped('machine_id').write({'status': 'breakdown'})

    def action_resolve(self):
        for rec in self:
            rec.write({'state': 'resolved', 'end_repair_datetime': fields.Datetime.now()})
            for line in rec.spare_used_ids:
                line.spare_id.write({
                    'current_stock': line.spare_id.current_stock - line.qty_used,
                })
            rec.machine_id.write({'status': 'running'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reset_reported(self):
        self.write({'state': 'reported'})


class FwBreakdownSpareLine(models.Model):
    _name = 'fw.breakdown.spare.line'
    _description = 'Breakdown Spare Part Consumption Line'
    _order = 'id'

    breakdown_id = fields.Many2one('fw.breakdown', string='Breakdown', required=True,
                                    ondelete='cascade')
    spare_id = fields.Many2one('fw.spare.part', string='Spare Part', required=True)
    available_stock = fields.Float(related='spare_id.current_stock', string='Available Stock')
    qty_used = fields.Float(string='Qty Used', required=True, default=1.0)
    remarks = fields.Char(string='Remarks')

    @api.constrains('qty_used')
    def _check_qty_used_non_negative(self):
        for rec in self:
            if rec.qty_used < 0:
                raise ValidationError("Qty Used cannot be negative.")
