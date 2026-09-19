# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwLineBooking(models.Model):
    _name = 'fw.line.booking'
    _description = 'Footwear Production Line Capacity Booking'
    _inherit = ['mail.thread']
    _order = 'date_start'

    name = fields.Char(string='Booking Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.line.booking') or 'New')
    production_line_id = fields.Many2one('fw.production.line', string='Production Line',
                                          required=True, tracking=True)
    factory_id = fields.Many2one(related='production_line_id.factory_id', string='Factory',
                                  store=True)
    rated_capacity = fields.Integer(related='production_line_id.rated_capacity_pairs_per_day',
                                     string='Rated Capacity (Pairs/Day)')

    buyer_order_id = fields.Many2one('fw.buyer.order', string='Buyer Order', tracking=True)
    style_id = fields.Many2one('fw.style', string='Style')

    date_start = fields.Date(string='Booking Start', required=True, tracking=True)
    date_end = fields.Date(string='Booking End', required=True, tracking=True)
    booked_qty = fields.Integer(string='Booked Qty (Pairs)', required=True, default=0)

    booked_days = fields.Integer(string='Booked Days', compute='_compute_days', store=True)
    required_days = fields.Float(string='Required Days (at Rated Capacity)',
                                  compute='_compute_days', store=True)
    is_overbooked = fields.Boolean(string='Overbooked', compute='_compute_days', store=True,
                                    help="True if the booked date range is shorter than the "
                                         "time required to produce the booked quantity at "
                                         "the line's rated capacity.")

    state = fields.Selection([
        ('planned', 'Planned'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='planned', tracking=True)

    color = fields.Integer(string='Color Index', compute='_compute_color', store=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.line.booking') or 'New'
        return super().create(vals_list)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError("Booking Start cannot be after Booking End.")

    @api.depends('date_start', 'date_end', 'booked_qty', 'rated_capacity')
    def _compute_days(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                rec.booked_days = (rec.date_end - rec.date_start).days + 1
            else:
                rec.booked_days = 0
            rec.required_days = (rec.booked_qty / rec.rated_capacity) \
                if rec.rated_capacity else 0.0
            rec.is_overbooked = bool(rec.booked_days) and rec.required_days > rec.booked_days

    @api.depends('production_line_id')
    def _compute_color(self):
        for rec in self:
            rec.color = (rec.production_line_id.id or 0) % 11

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_planned(self):
        self.write({'state': 'planned'})
