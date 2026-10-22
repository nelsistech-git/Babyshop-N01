# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Extends garment_finance's garment.export.documentation (Commercial
Invoice / Packing List / Shipping Instructions / Certificate of Origin)
with the rest of the Export Document Master list (SRS section 22), an
HS Code link, buyer-portal sharing, and invoice-line / packing-carton
detail (SRS sections 23-24)."""
from odoo import fields, models


class GarmentExportDocumentationExport(models.Model):
    _inherit = 'garment.export.documentation'

    # FIXED: Changed 'set null' to 'cascade' because the base field is required=True.
    # 'cascade' ensures that if this module is uninstalled, records using these
    # new selection options are safely deleted instead of violating the 'required' constraint.
    document_type = fields.Selection(selection_add=[
        ('exp_form_copy', 'EXP Form Copy'),
        ('gsp_certificate', 'GSP Certificate'),
        ('inspection_certificate', 'Inspection Certificate'),
        ('insurance_certificate', 'Insurance Certificate'),
        ('beneficiary_certificate', 'Beneficiary Certificate'),
    ], ondelete={
        'exp_form_copy': 'cascade',
        'gsp_certificate': 'cascade',
        'inspection_certificate': 'cascade',
        'insurance_certificate': 'cascade',
        'beneficiary_certificate': 'cascade',
    })

    po_number = fields.Char(string='PO Number')
    hs_code_id = fields.Many2one('garment.hs.code', string='HS Code')
    buyer_document_shared = fields.Boolean(string='Shared With Buyer (Portal)')

    line_ids = fields.One2many('garment.export.doc.line', 'document_id', string='Invoice Lines')
    carton_ids = fields.One2many('garment.export.doc.carton', 'document_id', string='Packing List Cartons')

    ai_verification_note = fields.Text(string='AI Document Verification', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Verified', readonly=True)

    def action_run_ai_verification(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            note = ai_engine.verify_commercial_documents(rec)
            rec.write({'ai_verification_note': note, 'ai_last_run': fields.Datetime.now()})
        return True

    def action_sync_totals_from_lines(self):
        """Recomputes total_quantity/total_value from invoice lines, and
        total_quantity/total_cartons/net-gross weight from packing cartons,
        instead of relying on manual entry."""
        for rec in self:
            if rec.line_ids:
                rec.total_quantity = sum(rec.line_ids.mapped('quantity'))
                rec.total_value = sum(rec.line_ids.mapped('amount'))
            if rec.carton_ids:
                rec.total_cartons = len(rec.carton_ids)
                rec.total_quantity = sum(rec.carton_ids.mapped('quantity')) or rec.total_quantity
        return True