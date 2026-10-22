# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentOrderDocument(models.Model):
    """Order Document Checklist (SRS sections 9, 17, 51) -
    garment.order.document. Tracks the buyer PO, tech pack, BOM, cost
    sheet, artwork, measurement chart, sample approval, inspection
    requirement and export documents required for the order.
    """
    _name = 'garment.order.document'
    _description = 'Garment Order Document Checklist'
    _order = 'order_id, id'

    order_id = fields.Many2one('garment.order', string='Order', required=True, ondelete='cascade')

    document_type = fields.Selection([
        ('buyer_po', 'Buyer PO'),
        ('tech_pack', 'Tech Pack'),
        ('measurement_sheet', 'Measurement Sheet'),
        ('specification_sheet', 'Specification Sheet'),
        ('artwork', 'Artwork'),
        ('bom', 'BOM'),
        ('cost_sheet', 'Cost Sheet'),
        ('measurement_chart', 'Measurement Chart'),
        ('sample_approval', 'Sample Approval'),
        ('inspection_requirement', 'Inspection Requirement'),
        ('approval_document', 'Approval Document'),
        ('commercial_invoice', 'Commercial Invoice'),
        ('packing_list', 'Packing List'),
        ('exp_form', 'EXP Form'),
        ('certificate_of_origin', 'Certificate of Origin'),
        ('bill_of_lading', 'Bill of Lading'),
        ('inspection_certificate', 'Inspection Certificate'),
    ], string='Document Type', required=True)

    attachment = fields.Binary(string='File', attachment=True)
    attachment_filename = fields.Char(string='File Name')
    status = fields.Selection([
        ('completed', 'Completed'), ('pending', 'Pending'), ('missing', 'Missing'),
    ], string='Status', default='pending')
    received_date = fields.Date(string='Received Date')
    remarks = fields.Char(string='Remarks')
