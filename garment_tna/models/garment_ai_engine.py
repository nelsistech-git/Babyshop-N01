# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with AI TNA Intelligence
(SRS section 19 / 29): shipment risk scoring, delay-probability estimate
from historical activity/supplier delay data, and schedule adjustment
suggestions. Rule-based, transparent, degrades gracefully.
"""
import logging
from datetime import date

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineTnaExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Shipment Risk Scoring
    # ------------------------------------------------------------------
    def _tna_risk_score(self, tna):
        """Shared, transparent scoring used by both predict_shipment_risk()
        and predict_shipment_probability() so the two AI outputs (SRS
        sections 19/29) never disagree with each other."""
        score = 0
        reasons = []

        critical_count = len(tna.activity_ids.filtered('is_critical_path'))
        if critical_count:
            score += min(30, critical_count * 5)
            reasons.append('%d activity(ies) currently on the critical path.' % critical_count)

        delays = tna.delay_ids
        severity_weight = {'normal': 0, 'low': 5, 'medium': 15, 'high': 30, 'critical': 45}
        for delay in delays:
            score += severity_weight.get(delay.severity, 0)
        if delays:
            worst = max(delays.mapped('severity'), key=lambda s: severity_weight.get(s, 0))
            reasons.append('%d delay(s) logged, worst severity: %s.' % (len(delays), worst))

        # Supplier delay history (reuses BOM supplier lead times if a BOM exists for the style)
        supplier_delays = delays.filtered(lambda d: d.delay_reason == 'supplier_delay' and d.supplier_id)
        for supplier in supplier_delays.mapped('supplier_id'):
            past_count = self.env['garment.tna.delay'].search_count([
                ('supplier_id', '=', supplier.id), ('delay_reason', '=', 'supplier_delay'),
            ])
            if past_count >= 3:
                score += 15
                reasons.append('Supplier "%s" has a history of %d delay(s) across TNAs — elevated risk.' % (
                    supplier.name, past_count))

        pending_milestones_overdue = tna.milestone_ids.filtered(
            lambda m: m.status == 'pending' and m.due_date and m.due_date < date.today())
        if pending_milestones_overdue:
            score += min(20, len(pending_milestones_overdue) * 10)
            reasons.append('%d milestone(s) overdue and still pending.' % len(pending_milestones_overdue))

        score = max(0, min(100, score))
        return score, reasons

    def predict_shipment_risk(self, tna):
        score, reasons = self._tna_risk_score(tna)
        if score >= 70:
            level = 'HIGH'
        elif score >= 35:
            level = 'MEDIUM'
        else:
            level = 'LOW'

        note = 'Shipment Risk: %s (score %d/100).' % (level, score)
        if reasons:
            note += '\n' + '\n'.join('- %s' % r for r in reasons)
        else:
            note += '\nNo significant risk factors detected.'
        return note

    # ------------------------------------------------------------------
    # AI Shipment Prediction (SRS section 29): Shipment Probability %,
    # Expected Delay (days) and a short Recommendation, from the same
    # rule-based score as predict_shipment_risk().
    # ------------------------------------------------------------------
    def predict_shipment_probability(self, tna):
        score, _reasons = self._tna_risk_score(tna)
        probability_pct = max(0, 100 - score)

        delay_days_logged = tna.delay_ids.mapped('delay_days')
        significant = [d for d in delay_days_logged if d > 0]
        if significant:
            expected_delay_days = round(sum(significant) / len(significant))
        elif score >= 70:
            expected_delay_days = max(1, round(score / 10))
        else:
            expected_delay_days = 0

        return probability_pct, expected_delay_days

    # ------------------------------------------------------------------
    # AI Schedule Adjustment Suggestion
    # ------------------------------------------------------------------
    def suggest_tna_schedule_adjustment(self, tna):
        suggestions = []
        critical_delayed = tna.activity_ids.filtered(
            lambda a: a.is_critical_path and a.status in ('delayed', 'pending', 'in_progress'))
        for activity in critical_delayed:
            if activity.status == 'delayed':
                suggestions.append('"%s" is delayed and on the critical path — expedite or reassign immediately.'
                                    % activity.activity_name)
            elif activity.planned_end_date and tna.shipment_date and \
                    (tna.shipment_date - activity.planned_end_date).days < 5:
                suggestions.append('"%s" finishes within 5 days of shipment with no buffer — consider moving '
                                    'the planned end date earlier.' % activity.activity_name)

        high_risk_milestones = tna.milestone_ids.filtered(lambda m: m.risk_level in ('high', 'critical'))
        for m in high_risk_milestones:
            suggestions.append('Milestone "%s" is flagged %s risk — review dependency chain before it blocks '
                                'downstream activities.' % (m.milestone_name, m.risk_level))

        if not suggestions:
            return 'No schedule adjustments suggested — critical path and milestones look on track.'
        return '\n'.join('- %s' % s for s in suggestions)
