# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Extends garment.ai.engine (garment_buyer_crm) with AI Commercial
Intelligence (SRS sections 38, 40): buyer commercial risk (payment
behaviour/bank/country risk — complements garment_finance's LC-specific
predict_lc_realization_risk) and rule-based commercial document
verification (missing documents, LC/invoice value mismatch). AI Shipment
Delay Prediction (SRS section 39) already exists on garment_logistics'
garment.shipment and is not duplicated here."""
from odoo import models

HIGH_RISK_COUNTRY_CODES = {'AF', 'SY', 'YE', 'SO', 'KP', 'IR'}


class GarmentAIEngineCommercialExportExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Buyer Commercial / LC Risk Prediction (SRS section 38)
    # ------------------------------------------------------------------
    def predict_buyer_commercial_risk(self, buyer):
        score = 0
        reasons = []

        rating_score = {'low': 0, 'medium': 20, 'high': 40}
        score += rating_score.get(buyer.risk_rating, 0)
        if buyer.risk_rating in ('medium', 'high'):
            reasons.append('Buyer master risk rating is "%s".' % buyer.risk_rating)

        receivables = self.env['garment.receivable'].search([
            ('buyer_id', '=', buyer.id), ('status', '!=', 'received'),
        ])
        overdue = receivables.filtered(lambda r: r.aging_bucket not in ('current',))
        if overdue:
            score += min(30, 10 * len(overdue))
            reasons.append('%d overdue receivable(s) outstanding for this buyer.' % len(overdue))

        country_code = buyer.country_id.code if buyer.country_id else False
        if country_code and country_code in HIGH_RISK_COUNTRY_CODES:
            score += 20
            reasons.append('Buyer country (%s) is on the elevated trade-risk watch list.' % buyer.country_id.name)

        if buyer.credit_limit and buyer.outstanding_balance and buyer.outstanding_balance > buyer.credit_limit:
            score += 15
            reasons.append('Outstanding balance exceeds the approved credit limit.')

        score = max(0, min(100, score))
        level = 'HIGH' if score >= 50 else 'MEDIUM' if score >= 25 else 'LOW'
        payment_probability = max(5, 100 - score)
        note = 'Buyer Commercial Risk: %s (score %d/100). Estimated payment probability: %d%%.' % (
            level, score, payment_probability)
        if reasons:
            note += '\n' + '\n'.join('- %s' % r for r in reasons)
        else:
            note += '\nNo significant risk factors detected.'
        return note

    # ------------------------------------------------------------------
    # AI Commercial Document Verification (SRS section 40)
    # ------------------------------------------------------------------
    def verify_commercial_documents(self, document):
        """document is a garment.export.documentation record."""
        issues = []

        if document.document_type == 'export_invoice':
            if not document.hs_code_id:
                issues.append('HS Code is not set on this Commercial Invoice.')
            if not document.po_number:
                issues.append('PO Number is missing on this Commercial Invoice.')
            if document.line_ids:
                line_total = sum(document.line_ids.mapped('amount'))
                if document.total_value and abs(line_total - document.total_value) > 0.01:
                    issues.append('Invoice line total (%.2f) does not match Total Value (%.2f).' % (
                        line_total, document.total_value))
            if document.lc_id and document.lc_id.lc_amount and document.total_value:
                if document.total_value > document.lc_id.lc_amount:
                    issues.append('Invoice value (%.2f) exceeds LC amount (%.2f) — LC mismatch.' % (
                        document.total_value, document.lc_id.lc_amount))
                elif document.lc_id.balance_amount and document.total_value > document.lc_id.balance_amount:
                    issues.append('Invoice value (%.2f) exceeds remaining LC balance (%.2f).' % (
                        document.total_value, document.lc_id.balance_amount))

        if document.document_type == 'packing_list' and document.carton_ids:
            carton_total = sum(document.carton_ids.mapped('quantity'))
            if document.total_quantity and carton_total != document.total_quantity:
                issues.append('Carton quantity total (%d) does not match Total Quantity (%d).' % (
                    carton_total, document.total_quantity))
            if len(document.carton_ids) != document.total_cartons:
                issues.append('Number of carton lines (%d) does not match Total Cartons (%d).' % (
                    len(document.carton_ids), document.total_cartons))

        if not document.filename and not document.file:
            issues.append('No scanned copy attached to this document.')

        if not issues:
            return 'Document Verification: PASSED — no missing or mismatched values detected.'
        return 'Document Verification: ISSUES FOUND\n' + '\n'.join('- %s' % i for i in issues)
