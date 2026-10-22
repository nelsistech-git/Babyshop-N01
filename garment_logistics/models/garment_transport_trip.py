# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Transport Request Management + Driver Assignment + Trip Management +
GPS Tracking Integration (SRS sections 22, 25-27) — garment.transport.trip.
A single model spans request -> assignment -> trip -> GPS, matching the
SRS's own 10-model DB design table which lists only garment.transport.trip.
"""
from odoo import api, fields, models, _


class GarmentTransportTrip(models.Model):
    _name = 'garment.transport.trip'
    _description = 'Garment Transport Trip'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    trip_number = fields.Char(string='Trip Number', copy=False, readonly=True, default=lambda s: _('New'))
    shipment_id = fields.Many2one('garment.shipment', string='Shipment')
    requested_by_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user)
    request_department = fields.Selection([
        ('commercial', 'Commercial Department'), ('logistics', 'Logistics Department'),
        ('warehouse', 'Warehouse Department'),
    ], string='Requested By Department')

    pickup_location = fields.Char(string='Pickup Location')
    delivery_location = fields.Char(string='Delivery Location')
    delivery_port_id = fields.Many2one('garment.port', string='Delivery Port')
    cargo_details = fields.Char(string='Cargo Details')
    requested_date = fields.Date(string='Requested Date', default=fields.Date.context_today)

    # Vehicle Requirement, requested before Vehicle Selection (SRS section 22)
    vehicle_requirement = fields.Selection([
        ('truck', 'Truck'), ('covered_van', 'Covered Van'),
        ('container_carrier', 'Container Carrier'), ('pickup', 'Pickup'),
    ], string='Vehicle Requirement')

    vehicle_id = fields.Many2one('garment.vehicle', string='Vehicle')
    driver_id = fields.Many2one('garment.driver', string='Driver')

    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    route = fields.Char(string='Route')
    distance_km = fields.Float(string='Distance (KM)')
    fuel_cost = fields.Monetary(string='Fuel Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    # GPS Tracking Integration (SRS section 27)
    current_location = fields.Char(string='Current Location (GPS)')
    estimated_arrival = fields.Char(string='Estimated Arrival Time')
    last_gps_update = fields.Datetime(string='Last GPS Update')

    status = fields.Selection([
        ('requested', 'Transport Request'), ('vehicle_selected', 'Vehicle Selection'),
        ('driver_assigned', 'Driver Assignment'), ('approved', 'Approval'), ('trip_started', 'Trip Start'),
        ('gate_pass', 'Gate Pass'), ('port_delivered', 'Port Delivery'), ('confirmed', 'Confirmation'),
    ], string='Status', default='requested', tracking=True, group_expand='_expand_states')

    # Port Delivery Tracking (SRS section 29): Factory Loaded -> In Transit
    # -> Port Gate Entry -> Port Accepted -> Vessel Loading.
    port_delivery_status = fields.Selection([
        ('factory_loaded', 'Factory Loaded'), ('in_transit', 'In Transit'),
        ('port_gate_entry', 'Port Gate Entry'), ('port_accepted', 'Port Accepted'),
        ('vessel_loading', 'Vessel Loading'),
    ], string='Port Delivery Status', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('trip_number', _('New')) == _('New'):
                vals['trip_number'] = self.env['ir.sequence'].next_by_code('garment.transport.trip') or _('New')
        return super().create(vals_list)

    def action_next_stage(self):
        flow = ['requested', 'vehicle_selected', 'driver_assigned', 'approved',
                'trip_started', 'gate_pass', 'port_delivered', 'confirmed']
        for rec in self:
            idx = flow.index(rec.status)
            if idx < len(flow) - 1:
                rec.status = flow[idx + 1]

    def action_next_port_delivery_status(self):
        """Port Delivery Tracking (SRS section 29)."""
        flow = ['factory_loaded', 'in_transit', 'port_gate_entry', 'port_accepted', 'vessel_loading']
        for rec in self:
            if not rec.port_delivery_status:
                rec.port_delivery_status = flow[0]
                continue
            idx = flow.index(rec.port_delivery_status)
            if idx < len(flow) - 1:
                rec.port_delivery_status = flow[idx + 1]
