# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentOrderColor(models.Model):
    """Color Information (SRS section 12) - garment.order.color.

    Detailed buyer/factory color codes, Pantone reference, lab dip and
    approval status for a colorway used on an Order Line.
    """
    _name = 'garment.order.color'
    _description = 'Garment Order Color Information'
    _order = 'order_line_id, id'

    order_line_id = fields.Many2one('garment.order.line', string='Order Line', required=True, ondelete='cascade')
    order_id = fields.Many2one(related='order_line_id.order_id', string='Order', store=True, readonly=True)

    color_name = fields.Char(string='Color Name', required=True)
    buyer_color_code = fields.Char(string='Buyer Color Code')
    factory_color_code = fields.Char(string='Factory Color Code')
    pantone_number = fields.Char(string='Pantone Number')
    shade_group = fields.Char(string='Shade Group')
    lab_dip_reference = fields.Char(string='Lab Dip Reference')
    approval_status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='pending')
    approval_date = fields.Date(string='Approval Date')
