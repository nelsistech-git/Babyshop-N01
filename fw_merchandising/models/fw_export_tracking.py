# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwExportTracking(models.Model):
    _name = 'fw.export.tracking'
    _description = 'Footwear Export Document Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Export Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.export.tracking') or 'New')
    shipment_id = fields.Many2one('fw.shipment', string='Shipment', required=True,
                                   ondelete='cascade', tracking=True)
    order_id = fields.Many2one(related='shipment_id.order_id', string='Buyer Order', store=True)
    buyer_id = fields.Many2one(related='shipment_id.buyer_id', string='Buyer', store=True)

    lc_no = fields.Char(string='L/C Number')
    lc_date = fields.Date(string='L/C Date')
    invoice_no = fields.Char(string='Commercial Invoice No.')
    invoice_date = fields.Date(string='Invoice Date')
    bl_awb_no = fields.Char(string='Bill of Lading / Airway Bill No.')
    customs_bill_no = fields.Char(string='Customs Bill of Export No.')

    document_status = fields.Selection([
        ('pending', 'Pending'),
        ('prepared', 'Prepared'),
        ('submitted', 'Submitted to Bank'),
        ('cleared', 'Customs Cleared'),
    ], string='Document Status', default='pending', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('documents_ready', 'Documents Ready'),
        ('customs_cleared', 'Customs Cleared'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)

    remarks = fields.Text(string='Remarks')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.export.tracking') or 'New'
        return super().create(vals_list)

    def action_set_documents_ready(self):
        self.write({'state': 'documents_ready', 'document_status': 'prepared'})

    def action_set_customs_cleared(self):
        self.write({'state': 'customs_cleared', 'document_status': 'cleared'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'document_status': 'pending'})
