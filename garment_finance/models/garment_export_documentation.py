# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Export Invoice Management + Packing List Management + Shipping Document
Management (SRS sections 34-36) — garment.export.documentation. Kept as
one model with a document_type split rather than three, since all three
share the same shipment/buyer/LC context and lifecycle.
"""
from odoo import api, fields, models, _


class GarmentExportDocumentation(models.Model):
    _name = 'garment.export.documentation'
    _description = 'Garment Export Documentation'
    _inherit = ['mail.thread']
    _order = 'document_date desc'

    document_number = fields.Char(string='Document Number', copy=False, readonly=True, default=lambda s: _('New'))
    document_type = fields.Selection([
        ('export_invoice', 'Export Invoice'), ('packing_list', 'Packing List'),
        ('shipping_instruction', 'Shipping Instructions'), ('certificate_of_origin', 'Certificate of Origin'),
    ], string='Document Type', required=True)
    shipment_id = fields.Many2one('garment.shipment', string='Shipment', required=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', related='shipment_id.buyer_id', store=True)
    lc_id = fields.Many2one('garment.lc', string='LC Reference')
    document_date = fields.Date(string='Document Date', default=fields.Date.context_today)
    total_quantity = fields.Integer(string='Total Quantity')
    total_cartons = fields.Integer(string='Total Cartons')
    total_value = fields.Monetary(string='Total Value', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    file = fields.Binary(string='File', attachment=True)
    filename = fields.Char(string='Filename')
    status = fields.Selection([
        ('draft', 'Draft'), ('issued', 'Issued'), ('submitted_to_bank', 'Submitted to Bank'), ('accepted', 'Accepted'),
    ], string='Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('document_number', _('New')) == _('New'):
                vals['document_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.export.documentation') or _('New')
        return super().create(vals_list)
