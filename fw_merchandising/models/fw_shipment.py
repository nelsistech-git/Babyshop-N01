# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError


class FwShipment(models.Model):
    _name = 'fw.shipment'
    _description = 'Footwear Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'shipment_date desc'

    name = fields.Char(string='Shipment Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.shipment') or 'New')
    order_id = fields.Many2one('fw.buyer.order', string='Buyer Order', required=True,
                                ondelete='cascade', tracking=True)
    buyer_id = fields.Many2one(related='order_id.buyer_id', string='Buyer', store=True)

    shipment_date = fields.Date(string='Shipment Date', default=fields.Date.context_today,
                                 tracking=True)
    mode = fields.Selection([
        ('sea', 'Sea Freight'),
        ('air', 'Air Freight'),
        ('road', 'Road / Land'),
    ], string='Mode of Shipment', default='sea', tracking=True)

    container_no = fields.Char(string='Container Number')
    vessel_flight_no = fields.Char(string='Vessel / Flight Number')
    port_of_loading = fields.Char(string='Port of Loading')
    port_of_discharge = fields.Char(string='Port of Discharge')

    invoice_value = fields.Monetary(string='Invoice Value', currency_field='currency_id')
    currency_id = fields.Many2one(related='order_id.currency_id', string='Currency', store=True)

    state = fields.Selection([
        ('planned', 'Planned'),
        ('booked', 'Booked'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    ], string='Status', default='planned', tracking=True)

    line_ids = fields.One2many('fw.shipment.line', 'shipment_id', string='Shipment Lines')
    total_qty_shipped = fields.Integer(string='Total Qty Shipped', compute='_compute_total_qty')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.shipment') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.qty_shipped')
    def _compute_total_qty(self):
        for rec in self:
            rec.total_qty_shipped = sum(rec.line_ids.mapped('qty_shipped'))

    def action_book(self):
        self.write({'state': 'booked'})

    def action_ship(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Cannot ship without any shipment lines.")
        self.write({'state': 'shipped'})
        for rec in self:
            if rec.order_id.state not in ('shipped', 'closed', 'cancelled'):
                rec.order_id.action_mark_shipped()

    def action_deliver(self):
        self.write({'state': 'delivered'})

    def action_reset_planned(self):
        self.write({'state': 'planned'})


class FwShipmentLine(models.Model):
    _name = 'fw.shipment.line'
    _description = 'Footwear Shipment Line'
    _order = 'id'

    shipment_id = fields.Many2one('fw.shipment', string='Shipment', required=True,
                                   ondelete='cascade')
    order_line_id = fields.Many2one('fw.buyer.order.line', string='Order Line', required=True)
    style_id = fields.Many2one(related='order_line_id.style_id', string='Style', store=True)
    color_id = fields.Many2one(related='order_line_id.color_id', string='Color', store=True)
    ordered_qty = fields.Integer(related='order_line_id.total_qty', string='Ordered Qty')
    qty_shipped = fields.Integer(string='Qty Shipped', required=True, default=0)
    carton_count = fields.Integer(string='Carton Count')
    remarks = fields.Char(string='Remarks')
