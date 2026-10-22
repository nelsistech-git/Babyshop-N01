# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Freight Cost Management + Freight Comparison System (SRS sections 15-16)
— garment.freight. Comparison is done by simply querying multiple
garment.freight records (one per forwarder quote) for the same shipment,
rather than a separate comparison model.
"""
from odoo import api, fields, models


class GarmentFreight(models.Model):
    _name = 'garment.freight'
    _description = 'Garment Freight Cost'
    _order = 'total_cost'

    shipment_id = fields.Many2one('garment.shipment', string='Shipment', required=True, ondelete='cascade')
    forwarder_id = fields.Many2one('garment.forwarder', string='Forwarder', required=True)
    currency_id = fields.Many2one('res.currency', related='shipment_id.currency_id', store=True)

    # Freight Cost Dashboard groupbys (SRS section 44): Freight by Buyer /
    # Country / Carrier / Monthly Trend.
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', related='shipment_id.buyer_id', store=True)
    destination = fields.Char(string='Destination (Country)', related='shipment_id.destination', store=True)
    shipment_date = fields.Date(string='Shipment Date', related='shipment_id.shipment_date', store=True)

    ocean_freight = fields.Monetary(string='Ocean/Air Freight', currency_field='currency_id')
    local_transport = fields.Monetary(string='Local Transport', currency_field='currency_id')
    port_charges = fields.Monetary(string='Port Charges', currency_field='currency_id')
    documentation_charge = fields.Monetary(string='Documentation Charge', currency_field='currency_id')
    handling_charge = fields.Monetary(string='Handling Charge', currency_field='currency_id')
    insurance = fields.Monetary(string='Insurance', currency_field='currency_id')
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_total_cost', store=True,
                                  currency_field='currency_id')

    transit_time_days = fields.Integer(string='Transit Time (days)')
    is_selected = fields.Boolean(string='Selected Quote')

    @api.depends('ocean_freight', 'local_transport', 'port_charges', 'documentation_charge',
                 'handling_charge', 'insurance')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = (rec.ocean_freight + rec.local_transport + rec.port_charges
                               + rec.documentation_charge + rec.handling_charge + rec.insurance)

    def action_select_quote(self):
        self.write({'is_selected': True})
        (self.shipment_id.freight_ids - self).write({'is_selected': False})
