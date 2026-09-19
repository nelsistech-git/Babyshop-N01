# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwSupplierDelivery(models.Model):
    _name = 'fw.supplier.delivery'
    _description = 'Footwear Supplier Delivery Performance'
    _order = 'promised_date desc'

    name = fields.Char(string='Delivery Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.supplier.delivery') or 'New')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True,
                                   domain="[('supplier_rank', '>', 0)]")
    po_reference = fields.Char(string='PO Reference')
    material_description = fields.Char(string='Material Description')

    promised_date = fields.Date(string='Promised Delivery Date', required=True)
    actual_delivery_date = fields.Date(string='Actual Delivery Date')

    delay_days = fields.Integer(string='Delay (Days)', compute='_compute_delay', store=True,
                                 help="Positive = late, zero or negative = on time or early.")
    on_time = fields.Boolean(string='On Time', compute='_compute_delay', store=True)

    remarks = fields.Char(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.supplier.delivery') or 'New'
        return super().create(vals_list)

    @api.depends('promised_date', 'actual_delivery_date')
    def _compute_delay(self):
        for rec in self:
            if rec.promised_date and rec.actual_delivery_date:
                rec.delay_days = (rec.actual_delivery_date - rec.promised_date).days
                rec.on_time = rec.delay_days <= 0
            else:
                rec.delay_days = 0
                rec.on_time = False
