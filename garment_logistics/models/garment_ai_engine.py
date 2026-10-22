# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with AI Logistics
Optimization (SRS sections 37-40): shipment delay prediction, forwarder
recommendation from cost/performance comparison, and container
utilization analysis. Rule-based, transparent, degrades gracefully.
"""
import logging
from datetime import date

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineLogisticsExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Shipment Delay Prediction (SRS section 38)
    # ------------------------------------------------------------------
    def predict_shipment_delay(self, shipment):
        reasons = []
        score = 0

        today = date.today()
        if shipment.shipment_date and shipment.shipment_date < today and shipment.status not in (
                'delivered',):
            score += 30
            reasons.append('Planned shipment date (%s) has already passed and shipment is not yet delivered.' %
                            shipment.shipment_date)

        stuck_containers = shipment.container_ids.filtered(
            lambda c: c.status in ('booked', 'empty_picked') and shipment.status in ('loading', 'port'))
        if stuck_containers:
            score += 25
            reasons.append('%d container(s) still not loaded while shipment status has moved to %s.' % (
                len(stuck_containers), shipment.status))

        pending_allocations = shipment.allocation_ids.filtered(lambda a: a.status != 'ready')
        if pending_allocations:
            score += 20
            reasons.append('%d allocation line(s) not yet fully ready.' % len(pending_allocations))

        missing_docs = ['bill_of_lading', 'freight_invoice'] if shipment.mode == 'sea' else ['airway_bill']
        have_docs = set(shipment.document_ids.mapped('document_type'))
        missing = [d for d in missing_docs if d not in have_docs]
        if missing:
            score += 15
            reasons.append('Missing document(s): %s.' % ', '.join(missing))

        if shipment.forwarder_id and shipment.forwarder_id.performance_rating and \
                shipment.forwarder_id.performance_rating < 80:
            score += 10
            reasons.append('Forwarder "%s" has a below-80%% performance rating (%.0f%%).' % (
                shipment.forwarder_id.name, shipment.forwarder_id.performance_rating))

        score = max(0, min(100, score))
        level = 'HIGH' if score >= 50 else 'MEDIUM' if score >= 25 else 'LOW'
        note = 'Delay Risk: %s (score %d/100).' % (level, score)
        if reasons:
            note += '\n' + '\n'.join('- %s' % r for r in reasons)
        else:
            note += '\nNo significant delay risk factors detected.'
        return note

    # ------------------------------------------------------------------
    # AI Forwarder Recommendation (from Freight Comparison, SRS section 16)
    # ------------------------------------------------------------------
    def recommend_forwarder(self, shipment):
        quotes = shipment.freight_ids
        if not quotes:
            return None, 'No freight quotes recorded yet for this shipment.'

        scored = []
        min_cost = min(quotes.mapped('total_cost')) or 0
        for q in quotes:
            score = 0.0
            if min_cost and q.total_cost:
                score += (min_cost / q.total_cost) * 60  # cost weight 60
            if q.forwarder_id.performance_rating:
                score += q.forwarder_id.performance_rating * 0.4  # performance weight 40
            scored.append((score, q))
        scored.sort(key=lambda t: t[0], reverse=True)
        best_score, best = scored[0]
        note = 'Recommended forwarder: %s (cost %.2f, transit %d days, rating %.0f%%, score %.1f/100).' % (
            best.forwarder_id.name, best.total_cost, best.transit_time_days or 0,
            best.forwarder_id.performance_rating or 0, best_score)
        return best.forwarder_id, note

    # ------------------------------------------------------------------
    # AI Freight Cost Prediction (SRS section 37)
    # ------------------------------------------------------------------
    def predict_freight_cost(self, shipment):
        """Analyzes historical freight (garment.freight) on the same route
        (destination) to project next-period cost movement, as a simple
        trend over the current shipment's freight quotes."""
        Freight = self.env['garment.freight']
        history = Freight.search([
            ('destination', '=', shipment.destination),
            ('shipment_id', '!=', shipment.id),
        ], order='shipment_date desc', limit=10)
        if not history:
            return 'AI Freight Cost Prediction: not enough historical freight data for route "%s" yet.' % (
                shipment.destination or '?')

        avg_cost = sum(history.mapped('total_cost')) / len(history)
        current_cost = shipment.total_freight_cost or avg_cost
        if not current_cost:
            return 'AI Freight Cost Prediction: no freight cost recorded yet for this shipment.'

        # Simple seasonal heuristic: Sep-Dec (peak export season in BD garment
        # trade) skews the projection upward, otherwise a mild variance band.
        month = (shipment.shipment_date or date.today()).month
        pct_change = 8.0 if month in (9, 10, 11, 12) else 3.0
        direction = 'Increase' if current_cost >= avg_cost else 'Decrease'
        projected = current_cost * (1 + pct_change / 100.0)
        return ('AI Freight Cost Prediction (route "%s"): current cost %.2f vs historical average %.2f '
                '(last %d shipment(s)). Next Month Projection: +%.0f%% %s -> approx. %.2f.') % (
            shipment.destination or '?', current_cost, avg_cost, len(history), pct_change, direction, projected)

    # ------------------------------------------------------------------
    # AI Route Optimization (SRS section 39)
    # ------------------------------------------------------------------
    def suggest_route_optimization(self, shipment):
        """Suggests the best carrier/route by comparing shipping lines
        serving the same destination on transit time."""
        ShippingLine = self.env['garment.shipping.line']
        candidates = ShippingLine.search([('destination_port', '=', shipment.destination)]) \
            if shipment.destination else ShippingLine.browse()
        if not candidates:
            candidates = ShippingLine.search([], limit=5)
        if not candidates:
            return 'AI Route Optimization: no shipping line data available yet.'

        current = shipment.shipping_line_id
        best = min(candidates, key=lambda sl: sl.transit_time_days or 9999)
        if not best.transit_time_days:
            return 'AI Route Optimization: no transit time data available for comparison.'

        current_days = current.transit_time_days if current and current.transit_time_days else best.transit_time_days
        saving = current_days - best.transit_time_days
        if current and current.id == best.id or saving <= 0:
            return ('AI Route Optimization: current route "%s" (%d days) is already the best available '
                    'option for this destination.') % (current.name if current else '?', current_days)
        return ('AI Route Optimization: Current Route %d Days -> AI Suggested "%s" %d Days '
                '(Saving %d Day(s)).') % (current_days, best.name, best.transit_time_days, saving)

    # ------------------------------------------------------------------
    # AI Container Utilization (SRS section 40)
    # ------------------------------------------------------------------
    def analyze_container_utilization(self, container):
        if not container.capacity_cbm:
            return 'No container capacity set — cannot assess utilization.'
        if container.utilization_pct < 70:
            return ('Utilization is low (%.0f%%) — consider consolidating with another shipment before '
                    'booking, or use a smaller container size.') % container.utilization_pct
        elif container.utilization_pct > 100:
            return 'Utilization exceeds 100%% (%.0f%%) — this container is over-booked, review loading plan.' % (
                container.utilization_pct)
        return 'Utilization is efficient (%.0f%%).' % container.utilization_pct
