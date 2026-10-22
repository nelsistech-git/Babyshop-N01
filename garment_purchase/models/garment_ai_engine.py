# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with AI Procurement
Intelligence (SRS sections 18, 39-40): supplier recommendation from
quotation comparison, material demand forecasting from open BOM
requirements, and purchase optimization suggestions. Rule-based,
transparent, degrades gracefully.
"""
import logging
from collections import defaultdict

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class GarmentAIEngineProcurementExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Purchase Recommendation (SRS section 18) / AI Supplier Selection
    # Engine (SRS section 41 — price, quality, delivery performance;
    # capacity/compliance/distance are scored by the Supplier module
    # (garment_supplier) which this module cannot depend on without a
    # dependency cycle, so they are out of scope here — see notes).
    # ------------------------------------------------------------------
    def recommend_purchase_supplier(self, rfq):
        quotations = rfq.quotation_ids
        if not quotations:
            return None, 'No quotations received yet for this RFQ.'

        scored = []
        prices = [q.price for q in quotations if q.price]
        min_price = min(prices) if prices else 0

        for q in quotations:
            score = 0.0
            if min_price and q.price:
                score += (min_price / q.price) * 40  # cheaper = higher score, weight 40
            score += (q.quality_rating_pct or 0) * 0.35  # weight 35
            score += (q.delivery_rating_pct or 0) * 0.20  # weight 20
            _risk_level, _reason = self.predict_delivery_risk(q.supplier_id)
            if _risk_level == 'low':
                score += 5
            elif _risk_level == 'high':
                score -= 5
            scored.append((score, q))

        scored.sort(key=lambda t: t[0], reverse=True)
        best_score, best = scored[0]
        reasons = []
        if best.quality_rating_pct and best.quality_rating_pct == max(q.quality_rating_pct or 0 for q in quotations):
            reasons.append('highest quality rating')
        if best.price == min_price:
            reasons.append('most competitive price')
        if best.delivery_rating_pct and best.delivery_rating_pct == max(
                q.delivery_rating_pct or 0 for q in quotations):
            reasons.append('best delivery performance record')

        note = 'Recommended supplier: %s (score %.1f/100).' % (best.supplier_id.name, best_score)
        if reasons:
            note += ' Reasons: ' + ', '.join(reasons) + '.'
        return best.supplier_id, note

    # ------------------------------------------------------------------
    # AI Demand Forecast (SRS section 39)
    # ------------------------------------------------------------------
    def forecast_material_demand(self, material_category=None):
        """Aggregate open (non-closed) BOM requirements by material as a
        simple, transparent demand forecast — no external ML model
        required, and always explainable."""
        domain = [('bom_id.status', 'not in', ('closed',))]
        totals = defaultdict(float)

        if material_category in (None, 'fabric'):
            fabrics = self.env['garment.fabric.bom'].search([('bom_id.status', 'not in', ('closed',))])
            for f in fabrics:
                totals[('fabric', f.fabric_role)] += f.required_qty or 0.0
        if material_category in (None, 'trim'):
            trims = self.env['garment.trim.bom'].search([('bom_id.status', 'not in', ('closed',))])
            for t in trims:
                totals[('trim', t.trim_type)] += t.required_qty or 0.0
        if material_category in (None, 'packaging'):
            packs = self.env['garment.packaging.bom'].search([('bom_id.status', 'not in', ('closed',))])
            for p in packs:
                totals[('packaging', p.packaging_type)] += p.required_qty or 0.0

        Forecast = self.env['garment.purchase.forecast']
        created = self.env['garment.purchase.forecast']
        period_start = fields.Date.today().replace(day=1)
        for (category, name), qty in totals.items():
            if qty <= 0:
                continue
            created |= Forecast.create({
                'material_category': category,
                'material_name': name or category,
                'forecast_period': period_start,
                'expected_requirement_qty': qty,
                'basis_note': 'Aggregated from all open (non-closed) BOM requirements at time of forecast.',
                'confidence_pct': 60.0,
            })
        return created

    # ------------------------------------------------------------------
    # AI Purchase Optimization (SRS section 40)
    # ------------------------------------------------------------------
    def suggest_purchase_optimization(self, requisition):
        suggestions = []

        # Consolidation: same material requested across multiple open requisitions for the same supplier.
        for line in requisition.line_ids:
            if not line.supplier_id:
                continue
            siblings = self.env['garment.purchase.request.line'].search([
                ('material_name', '=', line.material_name),
                ('supplier_id', '=', line.supplier_id.id),
                ('requisition_id', '!=', requisition.id),
                ('requisition_id.status', 'not in', ('closed', 'rejected')),
            ])
            if siblings:
                total_qty = line.purchase_qty + sum(siblings.mapped('purchase_qty'))
                suggestions.append('"%s" from %s: %d other open requisition(s) also need this material — '
                                    'consolidate into one PO for better pricing/MOQ (combined qty %.1f).' % (
                                        line.material_name, line.supplier_id.name, len(siblings), total_qty))

        if requisition.priority == 'low':
            suggestions.append('Priority is Low (future requirement) — consider batching with the next '
                                'planning cycle rather than raising a PO immediately.')

        if not suggestions:
            return 'No consolidation or timing optimization opportunities detected for this requisition.'
        return '\n'.join('- %s' % s for s in suggestions)

    # ------------------------------------------------------------------
    # AI Purchase Price Prediction (SRS section 41)
    # ------------------------------------------------------------------
    def predict_price_trend(self, material_name, material_category=None):
        """Compare the average unit price of the oldest vs. most recent
        third of this material's purchase order line history to derive a
        simple, explainable trend — no external market-data feed
        required."""
        Line = self.env['garment.purchase.order.line']
        lines = Line.search([('material_name', '=', material_name), ('unit_price', '>', 0)],
                             order='order_date asc')
        if len(lines) < 2:
            return None, _('Not enough purchase history for "%s" to predict a price trend.') % material_name

        third = max(1, len(lines) // 3)
        early_avg = sum(lines[:third].mapped('unit_price')) / third
        recent_avg = sum(lines[-third:].mapped('unit_price')) / third
        change_pct = ((recent_avg - early_avg) / early_avg * 100.0) if early_avg else 0.0

        if change_pct > 3:
            recommendation = _('Purchase before price increase — market trend is rising.')
        elif change_pct < -3:
            recommendation = _('Prices trending down — deferring non-urgent purchase may save cost.')
        else:
            recommendation = _('Prices are stable — no timing action recommended.')

        forecast = self.env['garment.purchase.forecast'].create({
            'forecast_type': 'price_prediction',
            'material_category': material_category,
            'material_name': material_name,
            'forecast_period': fields.Date.today().replace(day=1),
            'current_price': recent_avg,
            'predicted_price_change_pct': change_pct,
            'basis_note': _('Derived from %d historical purchase order line(s) for this material.') % len(lines),
            'recommendation': recommendation,
            'confidence_pct': min(90.0, 40.0 + len(lines) * 2),
        })
        return forecast, recommendation

    # ------------------------------------------------------------------
    # AI Purchase Delay Prediction (SRS section 41)
    # ------------------------------------------------------------------
    def predict_delivery_risk(self, supplier_partner, create_forecast=False):
        """Score a supplier's delivery risk from their last deliveries on
        record. Returns (risk_level, reason)."""
        if not supplier_partner:
            return 'medium', _('No supplier specified.')

        Delivery = self.env['garment.purchase.delivery']
        recent = Delivery.search([('supplier_id', '=', supplier_partner.id), ('actual_date', '!=', False)],
                                  order='actual_date desc', limit=3)
        if not recent:
            return 'medium', _('No delivery history yet for %s.') % supplier_partner.name

        delayed = recent.filtered(lambda d: d.delay_days > 0)
        if len(delayed) >= 2:
            risk_level, reason = 'high', _('Previous %d of %d deliveries were delayed.') % (
                len(delayed), len(recent))
        elif len(delayed) == 1:
            risk_level, reason = 'medium', _('1 of the last %d deliveries was delayed.') % len(recent)
        else:
            risk_level, reason = 'low', _('On-time delivery record for the last %d deliveries.') % len(recent)

        if create_forecast:
            self.env['garment.purchase.forecast'].create({
                'forecast_type': 'delay_risk',
                'forecast_period': fields.Date.today().replace(day=1),
                'supplier_id': supplier_partner.id,
                'risk_level': risk_level,
                'basis_note': reason,
                'recommendation': _('Assign backup supplier.') if risk_level == 'high' else _(
                    'No action required.'),
            })
        return risk_level, reason

    # ------------------------------------------------------------------
    # AI Automatic Purchase Planning (SRS section 41)
    # ------------------------------------------------------------------
    def generate_purchase_plan_suggestions(self):
        """Turn every demand forecast without a linked requisition yet
        into a draft Purchase Requisition."""
        Forecast = self.env['garment.purchase.forecast']
        pending = Forecast.search([('forecast_type', '=', 'demand'), ('requisition_id', '=', False),
                                    ('expected_requirement_qty', '>', 0)])
        pending.action_create_requisition()
        return pending.mapped('requisition_id')
