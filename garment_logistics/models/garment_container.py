# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentContainer(models.Model):
    """Container Management + Loading + Tracking Status (SRS sections
    10-12, 50) — garment.container."""
    _name = 'garment.container'
    _description = 'Garment Shipping Container'
    _inherit = ['mail.thread']
    _order = 'loading_date desc'

    container_no = fields.Char(string='Container Number', required=True, copy=False)
    shipment_id = fields.Many2one('garment.shipment', string='Shipment', required=True, ondelete='cascade')
    size = fields.Selection([
        ('20ft', '20 Feet'), ('40ft', '40 Feet'), ('40hc', '40 HC'),
    ], string='Size', required=True)
    container_type = fields.Char(string='Type')
    shipping_line_id = fields.Many2one('garment.shipping.line', string='Shipping Line')
    booking_number = fields.Char(string='Booking Number')
    seal_no = fields.Char(string='Seal Number')

    # Vessel Schedule (SRS section 18, folded in)
    vessel_name = fields.Char(string='Vessel Name')
    voyage_number = fields.Char(string='Voyage Number')
    etd = fields.Date(string='ETD (Estimated Departure)')
    eta = fields.Date(string='ETA (Estimated Arrival)')
    port = fields.Char(string='Port')
    port_id = fields.Many2one('garment.port', string='Loading/Discharge Port')
    current_location = fields.Char(string='Current Location',
                                    help='Real-Time Shipping Tracking Integration (SRS section 36) — '
                                         'vessel/container position, manually updated or synced from a '
                                         'shipping line / GPS tracking API.')

    # Loading Information (SRS section 11: Cartons Ready -> Loading Plan ->
    # Container Loading -> Seal Placement -> Dispatch)
    loading_date = fields.Date(string='Loading Date')
    carton_qty = fields.Integer(string='Carton Quantity')
    weight_kg = fields.Float(string='Weight (KG)')
    volume_cbm = fields.Float(string='Volume (CBM)')
    capacity_cbm = fields.Float(string='Container Capacity (CBM)')
    utilization_pct = fields.Float(string='Utilization %', compute='_compute_utilization', store=True)
    loading_person_id = fields.Many2one('res.users', string='Loading Person')
    dispatch_date = fields.Date(string='Dispatch Date')

    status = fields.Selection([
        ('booked', 'Booked'), ('empty_picked', 'Empty Picked'), ('factory_loading', 'Factory Loading'),
        ('loaded', 'Loaded'), ('port_arrival', 'Port Arrival'), ('vessel_departed', 'Vessel Departed'),
        ('destination_port', 'Destination Port'), ('delivered', 'Delivered'),
    ], string='Status', default='booked', tracking=True, group_expand='_expand_states')

    # AI Container Utilization (SRS section 40)
    ai_utilization_note = fields.Text(string='AI Utilization Analysis', readonly=True)

    @api.depends('volume_cbm', 'capacity_cbm')
    def _compute_utilization(self):
        for rec in self:
            rec.utilization_pct = (rec.volume_cbm / rec.capacity_cbm * 100.0) if rec.capacity_cbm else 0.0

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    def action_run_ai_utilization(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            rec.ai_utilization_note = ai_engine.analyze_container_utilization(rec)
        return True

    def action_next_status(self):
        """Advances container status and drives the Buyer Notification System
        and Delivery Completion Automation (SRS sections 35, 52): posts a
        message to the linked shipment (visible to buyer followers/portal)
        on the key milestones, and auto-closes the shipment once every one
        of its containers has been delivered."""
        flow = ['booked', 'empty_picked', 'factory_loading', 'loaded', 'port_arrival',
                'vessel_departed', 'destination_port', 'delivered']
        notify_labels = {
            'loaded': 'Container Loaded',
            'vessel_departed': 'Vessel Departed',
            'delivered': 'Delivery Completed',
        }
        for rec in self:
            idx = flow.index(rec.status)
            if idx < len(flow) - 1:
                new_status = flow[idx + 1]
                rec.status = new_status
                if new_status in notify_labels and rec.shipment_id:
                    status_label = dict(rec._fields['status'].selection).get(new_status, new_status)
                    rec.shipment_id.message_post(
                        body='%s: Container %s is now "%s".' % (
                            notify_labels[new_status], rec.container_no, status_label))
                if new_status == 'delivered' and rec.shipment_id:
                    rec.shipment_id._check_delivery_completion()
