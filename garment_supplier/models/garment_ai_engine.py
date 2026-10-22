# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with AI Supplier
Intelligence (SRS sections 30-31): risk prediction from delivery/quality
history (reusing Module 9's delivery data — no duplicate tracking), and
supplier recommendation by material from the product catalog and
scorecards. Rule-based, transparent, degrades gracefully.
"""
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineSupplierExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Supplier Risk Prediction (SRS section 30)
    # ------------------------------------------------------------------
    def predict_supplier_risk(self, supplier):
        score = 0
        reasons = []

        if supplier.is_blacklisted:
            return 'CRITICAL: Supplier is blacklisted (%s).' % (supplier.blacklist_reason or 'no reason on file')

        deliveries = self.env['garment.purchase.delivery'].search(
            [('supplier_id', '=', supplier.partner_id.id)]) if supplier.partner_id else self.env[
            'garment.purchase.delivery']
        delayed = deliveries.filtered(lambda d: d.delay_days > 0)
        if deliveries:
            delay_rate = len(delayed) / len(deliveries) * 100.0
            if delay_rate > 30:
                score += 30
                reasons.append('%.0f%% of past deliveries were late (%d of %d).' % (
                    delay_rate, len(delayed), len(deliveries)))
            elif delay_rate > 10:
                score += 15
                reasons.append('%.0f%% of past deliveries were late.' % delay_rate)

        latest_rating = supplier.rating_ids.sorted('rating_date', reverse=True)[:1]
        if latest_rating:
            if latest_rating.quality_score and latest_rating.quality_score < 70:
                score += 25
                reasons.append('Latest quality score is low (%.0f%%).' % latest_rating.quality_score)
            if latest_rating.final_score and latest_rating.final_score < 60:
                score += 20
                reasons.append('Latest overall scorecard is Restricted-tier (%.0f%%).' % latest_rating.final_score)
        else:
            reasons.append('No performance rating on file yet — risk assessment is less reliable.')

        expiring_docs = supplier.document_ids.filtered(lambda d: d.expiry_status in ('expiring_soon', 'expired'))
        if expiring_docs:
            score += min(15, len(expiring_docs) * 5)
            reasons.append('%d document(s) expiring soon or already expired.' % len(expiring_docs))

        open_risks = supplier.risk_ids.filtered(lambda r: r.status != 'closed')
        critical_open = open_risks.filtered(lambda r: r.risk_level in ('high', 'critical'))
        if critical_open:
            score += min(20, len(critical_open) * 10)
            reasons.append('%d open high/critical risk record(s).' % len(critical_open))

        score = max(0, min(100, score))
        level = 'CRITICAL' if score >= 70 else 'HIGH' if score >= 45 else 'MEDIUM' if score >= 20 else 'LOW'
        note = 'Predicted Risk: %s (score %d/100).' % (level, score)
        if reasons:
            note += '\n' + '\n'.join('- %s' % r for r in reasons)
        else:
            note += '\nNo significant risk indicators found.'
        return note

    # ------------------------------------------------------------------
    # AI Supplier Recommendation (SRS section 31)
    # ------------------------------------------------------------------
    def recommend_suppliers_for_material(self, material_name, limit=5):
        products = self.env['garment.supplier.product'].search([
            ('product_name', 'ilike', material_name),
            ('supplier_id.is_blacklisted', '=', False),
            ('supplier_id.status', '=', 'active'),
        ], limit=50)
        if not products:
            return self.env['garment.supplier'], 'No active, non-blacklisted suppliers found carrying "%s".' % material_name

        scored = []
        for product in products:
            supplier = product.supplier_id
            score = (supplier.rating or 0) * 0.7
            if product.unit_price:
                score += 15  # has a price on file, more usable
            if product.lead_time_days and product.lead_time_days <= 30:
                score += 15
            scored.append((score, supplier, product))

        scored.sort(key=lambda t: t[0], reverse=True)
        top = scored[:limit]
        suppliers = self.env['garment.supplier'].browse([s.id for _sc, s, _p in top]).exists()
        note = 'Top match(es) for "%s": %s.' % (
            material_name, ', '.join('%s (score %d, rating %.0f%%)' % (s.name, sc, s.rating) for sc, s, _p in top))
        return suppliers, note
