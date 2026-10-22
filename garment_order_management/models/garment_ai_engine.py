# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with AI Order Intelligence
(SRS sections 19, 46-48): Order Risk Prediction, Delivery Prediction and
Factory/Line Allocation Optimization. Rule-based and transparent so it
always works, with or without an external AI provider configured (the
scoring inputs below - TNA progress, material status, production
efficiency/progress, historical delays - are exactly the ones the SRS
lists as AI inputs).
"""
import logging
from datetime import timedelta

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineOrderExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Order Risk Prediction (SRS sections 18-19, 46)
    # ------------------------------------------------------------------
    def predict_order_risk(self, order):
        """Return (score: float 0-100, level: 'LOW'/'MEDIUM'/'HIGH'/'CRITICAL',
        reason: str, recommendation: str)."""
        score = 0.0
        reasons = []
        recommendations = []

        # TNA progress signal
        if order.tna_id:
            tna_progress = order.tna_id.progress or 0.0
            if tna_progress < 40:
                score += 20
                reasons.append('TNA progress is only %.0f%%.' % tna_progress)
                recommendations.append('Expedite TNA critical-path activities.')
        elif order.state not in ('draft', 'po_received'):
            score += 10
            reasons.append('No TNA plan linked to this order yet.')
            recommendations.append('Create/link a TNA plan.')

        # Material availability signal
        material_weight = {'available': 0, 'partial': 15, 'shortage': 30, 'delayed': 40}
        score += material_weight.get(order.material_status, 0)
        if order.material_status in ('shortage', 'delayed'):
            reasons.append('Material status is "%s" (shortage %.0f).' % (
                order.material_status, order.shortage_qty or 0.0))
            recommendations.append('Increase supplier priority / expedite fabric or trim delivery.')

        # Production efficiency / progress signal
        if order.state == 'production_running' and order.progress < 50:
            score += 15
            reasons.append('Overall production progress is only %.0f%% while in Production Running.' %
                            order.progress)
            recommendations.append('Add overtime or move production to a faster line.')

        # Capacity shortage signal
        if order.capacity_shortage_qty:
            score += 15
            reasons.append('Capacity shortage of %s pcs.' % order.capacity_shortage_qty)
            recommendations.append('Allocate additional production line or subcontract the shortfall.')

        # Historical delay signal
        open_delays = order.delay_ids.filtered(lambda d: d.status != 'resolved')
        if open_delays:
            score += min(20, len(open_delays) * 8)
            reasons.append('%d unresolved delay(s) on record.' % len(open_delays))
            recommendations.append('Execute the logged recovery plan(s).')

        score = max(0.0, min(100.0, score))
        if score >= 75:
            level = 'CRITICAL'
        elif score >= 50:
            level = 'HIGH'
        elif score >= 25:
            level = 'MEDIUM'
        else:
            level = 'LOW'

        reason = ' '.join(reasons) if reasons else 'No significant risk factors detected.'
        recommendation = ' '.join(sorted(set(recommendations))) if recommendations else \
            'Continue monitoring - order is tracking on plan.'
        return score, level, reason, recommendation

    # ------------------------------------------------------------------
    # AI Delivery Prediction (SRS section 47)
    # ------------------------------------------------------------------
    def predict_order_delivery(self, order):
        """Return (predicted_date, delay_probability_pct)."""
        if not order.shipment_date:
            return False, 0.0

        delay_days = 0
        probability = 0.0

        if order.progress < 100:
            remaining_pct = 100 - (order.progress or 0.0)
            # Rough heuristic: every 10 points of remaining progress costs ~1 buffer day
            # once the order is already inside its execution stages.
            if order.state in ('production_running', 'quality_checking', 'ready_for_shipment'):
                delay_days += int(remaining_pct / 10)
                probability += min(60.0, remaining_pct)

        material_bump = {'available': 0, 'partial': 3, 'shortage': 7, 'delayed': 10}
        delay_days += material_bump.get(order.material_status, 0)
        if order.material_status in ('shortage', 'delayed'):
            probability += 20.0

        open_delays = order.delay_ids.filtered(lambda d: d.status != 'resolved')
        for delay in open_delays:
            delay_days += delay.delay_days or 0
        if open_delays:
            probability += min(30.0, len(open_delays) * 10)

        probability = max(0.0, min(100.0, probability))
        predicted_date = order.shipment_date + timedelta(days=delay_days) if delay_days else order.shipment_date
        return predicted_date, probability

    # ------------------------------------------------------------------
    # AI Order / Factory Allocation Optimization (SRS section 48)
    # ------------------------------------------------------------------
    def optimize_order_allocation(self, order):
        suggestions = []

        if order.capacity_shortage_qty:
            candidate = self.env['garment.order.allocation'].search([
                ('order_id', '!=', order.id),
                ('production_status', 'in', ('pending', 'material_ready')),
            ], limit=1, order='allocated_qty asc')
            if candidate:
                suggestions.append(
                    'Consider moving %s pcs from Line "%s" (Order %s) to free capacity for Order %s - '
                    'estimated recovery a few days once reallocated.' % (
                        order.capacity_shortage_qty, candidate.production_line or candidate.factory,
                        candidate.order_id.name, order.name))
            else:
                suggestions.append(
                    'Capacity shortage of %s pcs - no idle line found; consider subcontracting or '
                    'overtime for Order %s.' % (order.capacity_shortage_qty, order.name))

        overdue_allocations = order.allocation_ids.filtered(
            lambda a: a.delivery_date and a.delivery_date < a.order_id.shipment_date
            and a.production_status not in ('completed',))
        for alloc in overdue_allocations:
            suggestions.append('Factory "%s" allocation (%s pcs) is behind its %s delivery date - '
                                'prioritize or reassign.' % (alloc.factory, alloc.allocated_qty,
                                                              alloc.delivery_date))

        if order.material_status in ('shortage', 'delayed'):
            suggestions.append('Raise material priority / switch supplier to protect the %s shipment date.' %
                                (order.shipment_date or '-'))

        if not suggestions:
            return 'No optimization action recommended - allocation and capacity look on track.'
        return '\n'.join('- %s' % s for s in suggestions)
