# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentBillLading(models.Model):
    """Bill of Lading Management (SRS section 30) — garment.bill.lading."""
    _name = 'garment.bill.lading'
    _description = 'Garment Bill of Lading'
    _inherit = ['mail.thread']
    _order = 'date desc'

    bl_number = fields.Char(string='B/L Number', copy=False, readonly=True, default=lambda s: _('New'))
    shipment_id = fields.Many2one('garment.shipment', string='Shipment', required=True, ondelete='cascade')
    vessel_name = fields.Char(string='Vessel')
    container_id = fields.Many2one('garment.container', string='Container', domain="[('shipment_id', '=', shipment_id)]")
    port = fields.Char(string='Port')
    consignee = fields.Char(string='Consignee')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    status = fields.Selection([
        ('draft', 'Draft'), ('issued', 'Issued'), ('surrendered', 'Surrendered'), ('released', 'Released'),
    ], string='Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('bl_number', _('New')) == _('New'):
                vals['bl_number'] = self.env['ir.sequence'].next_by_code('garment.bill.lading') or _('New')
        return super().create(vals_list)
