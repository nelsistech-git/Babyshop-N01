# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Chemical Management System (SRS1 secs. 37-38, SRS2 secs. 59-62) —
garment.compliance.chemical. This is the COMPLIANCE/SAFETY register (SDS,
ZDHC MRSL status, storage inspection, usage-approval workflow) — actual
stock quantity/valuation of chemical items already lives on
garment.material (category='chemical') in garment_warehouse; this model
links to it optionally rather than duplicating inventory fields.
"""
from odoo import fields, models


class GarmentComplianceChemical(models.Model):
    _name = 'garment.compliance.chemical'
    _description = 'Garment Compliance Chemical Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Chemical Name', required=True)
    material_id = fields.Many2one('garment.material', string='Material Item', domain=[('category', '=', 'chemical')],
                                   help='Optional link to the stock item master for quantity/valuation.')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    storage_location_id = fields.Many2one('garment.location', string='Storage Location')
    quantity = fields.Float(string='Quantity on Hand')
    uom = fields.Char(string='Unit', default='KG')
    hazard_class = fields.Char(string='Hazard Class')
    sds_available = fields.Boolean(string='SDS Available')
    sds_attachment = fields.Binary(string='Safety Data Sheet', attachment=True)
    sds_attachment_filename = fields.Char(string='SDS Filename')
    expiry_date = fields.Date(string='Expiry Date')
    zdhc_mrsl_status = fields.Selection([
        ('compliant', 'ZDHC MRSL Compliant'), ('restricted', 'Restricted Use'),
        ('banned', 'Banned Substance'), ('pending_review', 'Pending Review'),
    ], string='ZDHC MRSL Status', default='pending_review', tracking=True)
    ppe_requirement = fields.Char(string='PPE Requirement')
    emergency_procedure = fields.Text(string='Emergency Procedure')
    approval_status = fields.Selection([
        ('requested', 'New Chemical Requested'), ('compliance_review', 'Compliance Review'),
        ('safety_approval', 'Safety Approval'), ('purchase_permitted', 'Purchase Permission Granted'),
        ('usage_allowed', 'Usage Allowed'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='requested', tracking=True)

    def action_next_approval_stage(self):
        flow = ['requested', 'compliance_review', 'safety_approval', 'purchase_permitted', 'usage_allowed']
        for rec in self:
            if rec.approval_status in flow:
                idx = flow.index(rec.approval_status)
                if idx < len(flow) - 1:
                    rec.approval_status = flow[idx + 1]
