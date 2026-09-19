# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
import math

from odoo import api, fields, models
from odoo.exceptions import UserError


class FwLineBalancing(models.Model):
    _name = 'fw.line.balancing'
    _description = 'Footwear Line Balancing Sheet'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Balancing Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.line.balancing') or 'New')
    style_id = fields.Many2one('fw.style', string='Style', required=True, tracking=True)
    production_line_id = fields.Many2one('fw.production.line', string='Production Line',
                                          required=True, tracking=True)
    factory_id = fields.Many2one(related='production_line_id.factory_id', string='Factory',
                                  store=True)

    target_output_per_day = fields.Integer(string='Target Output (Pairs/Day)', required=True,
                                            default=0)
    working_minutes_per_day = fields.Float(string='Working Minutes/Day', default=480.0,
                                            help="Effective working minutes per shift, "
                                                 "e.g. 480 for an 8-hour shift.")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many('fw.line.balancing.line', 'balancing_id', string='Operations')

    cycle_time = fields.Float(string='Cycle Time / Takt Time (min per pair)',
                               compute='_compute_summary', store=True, digits=(8, 4),
                               help="Working Minutes per Day / Target Output per Day. "
                                    "The maximum time allowed per pair to hit the target.")
    total_smv = fields.Float(string='Total SMV (min)', compute='_compute_summary', store=True,
                              digits=(8, 4))
    total_manpower = fields.Integer(string='Total Manpower Required',
                                     compute='_compute_summary', store=True)
    line_efficiency_percent = fields.Float(string='Line Balancing Efficiency (%)',
                                            compute='_compute_summary', store=True)
    achievable_output = fields.Integer(string='Achievable Output with Assigned Manpower',
                                        compute='_compute_summary', store=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.line.balancing') or 'New'
        return super().create(vals_list)

    @api.depends('target_output_per_day', 'working_minutes_per_day', 'line_ids.smv',
                 'line_ids.manpower_required')
    def _compute_summary(self):
        for rec in self:
            rec.cycle_time = (rec.working_minutes_per_day / rec.target_output_per_day) \
                if rec.target_output_per_day else 0.0
            rec.total_smv = sum(rec.line_ids.mapped('smv'))
            rec.total_manpower = sum(rec.line_ids.mapped('manpower_required'))
            denominator = rec.total_manpower * rec.cycle_time
            rec.line_efficiency_percent = (rec.total_smv / denominator * 100.0) \
                if denominator else 0.0
            rec.achievable_output = int(
                (rec.total_manpower * rec.working_minutes_per_day) / rec.total_smv) \
                if rec.total_smv else 0

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Cannot confirm a line balancing sheet with no operations.")
        self.write({'state': 'confirmed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class FwLineBalancingLine(models.Model):
    _name = 'fw.line.balancing.line'
    _description = 'Footwear Line Balancing Operation Line'
    _order = 'sequence, id'

    balancing_id = fields.Many2one('fw.line.balancing', string='Line Balancing', required=True,
                                    ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    operation_id = fields.Many2one('fw.operation', string='Operation', required=True)
    smv = fields.Float(string='SMV (min)', required=True, digits=(8, 4))
    workstation_no = fields.Char(string='Workstation No.')
    assigned_operator_id = fields.Many2one('hr.employee', string='Assigned Operator')

    cycle_time = fields.Float(related='balancing_id.cycle_time', string='Cycle Time')
    manpower_required = fields.Integer(string='Manpower Required',
                                        compute='_compute_manpower', store=True)
    is_bottleneck = fields.Boolean(string='Bottleneck', compute='_compute_manpower', store=True)

    @api.onchange('operation_id')
    def _onchange_operation_id(self):
        if self.operation_id and self.operation_id.standard_smv:
            self.smv = self.operation_id.standard_smv

    @api.depends('smv', 'balancing_id.cycle_time')
    def _compute_manpower(self):
        for rec in self:
            cycle_time = rec.balancing_id.cycle_time
            if cycle_time:
                rec.manpower_required = math.ceil(rec.smv / cycle_time) if rec.smv else 0
                rec.is_bottleneck = rec.smv > cycle_time
            else:
                rec.manpower_required = 0
                rec.is_bottleneck = False
