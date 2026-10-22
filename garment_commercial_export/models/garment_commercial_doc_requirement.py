# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Buyer-specific documentation requirements + Commercial Document
Checklist (SRS section 20). Each buyer can require a different subset of
the Export Document Master (SRS section 22) list to be present before a
shipment is considered document-ready; garment.shipment's
_compute_commercial_readiness (garment_shipment_export.py) checks a
shipment's buyer against this checklist."""
from odoo import fields, models

DOCUMENT_TYPE_SELECTION = [
    ('pi', 'Proforma Invoice'), ('lc_copy', 'LC Copy'), ('export_invoice', 'Commercial Invoice'),
    ('packing_list', 'Packing List'), ('exp_form', 'EXP Form'), ('bill_of_lading', 'Bill of Lading / AWB'),
    ('certificate_of_origin', 'Certificate of Origin'), ('gsp_certificate', 'GSP Certificate'),
    ('inspection_certificate', 'Inspection Certificate'), ('insurance_certificate', 'Insurance Certificate'),
    ('beneficiary_certificate', 'Beneficiary Certificate'),
]


class GarmentCommercialDocRequirement(models.Model):
    _name = 'garment.commercial.doc.requirement'
    _description = 'Garment Buyer Commercial Document Requirement'
    _order = 'buyer_id, sequence'

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    document_type = fields.Selection(DOCUMENT_TYPE_SELECTION, string='Document Type', required=True)
    is_mandatory = fields.Boolean(string='Mandatory', default=True)
    notes = fields.Char(string='Buyer-Specific Notes')

    _sql_constraints = [
        ('buyer_doc_type_uniq', 'unique(buyer_id, document_type)',
         'This document type is already listed for this buyer!'),
    ]
