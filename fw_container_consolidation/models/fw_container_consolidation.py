# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwContainerConsolidation(models.Model):
    _name = 'fw.container.consolidation'
    _description = 'Footwear Container / Vessel Consolidation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'etd desc'

    name = fields.Char(string='Consolidation Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.container.consolidation') or 'New')
    mode = fields.Selection([
        ('sea', 'Sea Freight'),
        ('air', 'Air Freight'),
        ('road', 'Road / Land'),
    ], string='Mode', default='sea', required=True)

    container_no = fields.Char(string='Container Number')
    vessel_flight_no = fields.Char(string='Vessel / Flight Number')
    booking_ref = fields.Char(string='Freight Forwarder Booking Ref.')

    port_of_loading = fields.Char(string='Port of Loading')
    port_of_discharge = fields.Char(string='Port of Discharge')
    etd = fields.Date(string='ETD (Estimated Departure)')
    eta = fields.Date(string='ETA (Estimated Arrival)')

    container_capacity_cbm = fields.Float(string='Container Capacity (CBM)',
                                           help="Reference only, e.g. ~28 CBM for a 20ft "
                                                "container, ~58 CBM for a 40ft container.")

    shipment_ids = fields.One2many('fw.shipment', 'consolidation_id', string='Shipments')
    shipment_count = fields.Integer(string='Shipments', compute='_compute_aggregates',
                                     store=True)
    total_qty_shipped = fields.Integer(string='Total Qty (All Shipments)',
                                        compute='_compute_aggregates', store=True)
    total_gross_weight = fields.Float(string='Total Gross Weight (kg)',
                                       compute='_compute_aggregates', store=True)
    total_carton_count = fields.Integer(string='Total Cartons', compute='_compute_aggregates',
                                         store=True)

    state = fields.Selection([
        ('planning', 'Planning'),
        ('booked', 'Booked'),
        ('in_transit', 'In Transit'),
        ('arrived', 'Arrived'),
        ('closed', 'Closed'),
    ], string='Status', default='planning', tracking=True)

    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.container.consolidation') or 'New'
        return super().create(vals_list)

    @api.depends('shipment_ids.total_qty_shipped')
    def _compute_aggregates(self):
        for rec in self:
            rec.shipment_count = len(rec.shipment_ids)
            rec.total_qty_shipped = sum(rec.shipment_ids.mapped('total_qty_shipped'))
            cartons = self.env['fw.carton'].search([
                ('shipment_id', 'in', rec.shipment_ids.ids),
            ]) if rec.shipment_ids else self.env['fw.carton']
            rec.total_gross_weight = sum(cartons.mapped('gross_weight'))
            rec.total_carton_count = len(cartons)

    def action_book(self):
        self.write({'state': 'booked'})

    def action_in_transit(self):
        self.write({'state': 'in_transit'})

    def action_arrived(self):
        self.write({'state': 'arrived'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reset_planning(self):
        self.write({'state': 'planning'})
