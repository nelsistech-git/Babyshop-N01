# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Capacity Planning System / Production Simulation (SRS s.26-28, s.37, s.44) —
IE what-if capacity engineering: given operators, working hours, SMV and
efficiency, compute daily capacity per line and, for an order quantity, the
required number of lines / estimated completion days / delivery risk.

Note: ``garment_production`` already carries a per-line/date operational
``garment.capacity.plan`` (booked vs. remaining capacity for planning). This
model is the IE-side simulation/what-if tool used before a line is
committed, and also rolls up to a factory-level booked-vs-available figure
(SRS s.27) — it is not a duplicate of the day-to-day planning record.
"""
import math

from odoo import api, fields, models, _


class GarmentIeCapacityStudy(models.Model):
    _name = 'garment.ie.capacity.study'
    _description = 'Garment IE Capacity Study'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'study_number'

    study_number = fields.Char(string='Study Reference', copy=False, readonly=True, default=lambda s: _('New'))
    study_type = fields.Selection([
        ('factory_capacity', 'Factory Capacity Planning'),
        ('order_simulation', 'Order / Production Simulation'),
        ('forecast', 'Capacity Forecast'),
    ], string='Study Type', default='order_simulation', required=True, tracking=True)
    style_id = fields.Many2one('garment.style', string='Style')
    production_order_id = fields.Many2one('garment.production.order', string='Production Order')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)

    order_qty = fields.Float(string='Order Quantity (PCS)')
    available_lines = fields.Integer(string='Available Lines', default=1)
    operators_per_line = fields.Integer(string='Operators per Line', default=45)
    working_hours = fields.Float(string='Working Hours', default=10.0)
    smv = fields.Float(string='SMV (Minutes)', digits=(6, 3))
    efficiency_pct = fields.Float(string='Efficiency (%)', default=70.0)

    daily_capacity_per_line = fields.Float(string='Daily Capacity per Line (PCS)',
                                            compute='_compute_capacity', store=True)
    total_daily_capacity = fields.Float(string='Total Daily Capacity (PCS)', compute='_compute_capacity', store=True)
    monthly_capacity = fields.Float(string='Monthly Capacity (PCS)', compute='_compute_capacity', store=True,
                                     help='Total daily capacity x 26 working days/month.')

    target_delivery_days = fields.Integer(string='Target Delivery (Days)')
    required_lines = fields.Integer(string='Required Lines', compute='_compute_simulation', store=True)
    estimated_completion_days = fields.Float(string='Estimated Completion (Days)',
                                              compute='_compute_simulation', store=True)
    risk_level = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], string='Delivery Risk', compute='_compute_simulation', store=True)

    booked_qty = fields.Float(string='Booked Quantity (PCS/Month)')
    available_capacity = fields.Float(string='Available Capacity (PCS/Month)', compute='_compute_capacity',
                                       store=True)

    notes = fields.Text(string='Notes')
    status = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], string='Status',
                               default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('operators_per_line', 'working_hours', 'efficiency_pct', 'smv', 'available_lines', 'booked_qty')
    def _compute_capacity(self):
        for rec in self:
            if rec.smv:
                available_minutes = rec.operators_per_line * rec.working_hours * 60.0
                rec.daily_capacity_per_line = (available_minutes * (rec.efficiency_pct / 100.0)) / rec.smv
            else:
                rec.daily_capacity_per_line = 0.0
            rec.total_daily_capacity = rec.daily_capacity_per_line * rec.available_lines
            rec.monthly_capacity = rec.total_daily_capacity * 26
            rec.available_capacity = rec.monthly_capacity - rec.booked_qty

    @api.depends('order_qty', 'daily_capacity_per_line', 'total_daily_capacity', 'target_delivery_days',
                 'available_lines')
    def _compute_simulation(self):
        for rec in self:
            if rec.target_delivery_days and rec.daily_capacity_per_line:
                rec.required_lines = math.ceil(
                    rec.order_qty / (rec.daily_capacity_per_line * rec.target_delivery_days))
            else:
                rec.required_lines = 0
            rec.estimated_completion_days = (rec.order_qty / rec.total_daily_capacity
                                              if rec.total_daily_capacity else 0.0)
            if not rec.order_qty:
                rec.risk_level = False
            elif rec.required_lines and rec.required_lines > rec.available_lines:
                rec.risk_level = 'high'
            elif rec.target_delivery_days and rec.estimated_completion_days > rec.target_delivery_days:
                rec.risk_level = 'medium'
            else:
                rec.risk_level = 'low'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('study_number', _('New')) == _('New'):
                vals['study_number'] = self.env['ir.sequence'].next_by_code('garment.ie.capacity.study') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'status': 'confirmed'})
