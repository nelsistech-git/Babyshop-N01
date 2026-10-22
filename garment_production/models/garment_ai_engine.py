# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (defined in garment_buyer_crm) with Production
Optimization features: completion/delay forecasting (Production Management
SRS s.39-40/55, Planning & MES SRS s.39-40/51, MES SRS s.39/49-52, Shop
Floor SRS s.35/38) and Predictive Machine Maintenance. Falls back to a
deterministic heuristic scorer so the feature always works without an
external AI provider configured.
"""
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class GarmentAIEngineProductionExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    def predict_production_completion(self, production_order):
        """Return (predicted_completion_date, risk, insight_text)."""
        order = production_order
        today = fields.Date.context_today(self)
        qty = order.quantity or 0.0
        done_pct = order.packing_pct or 0.0

        if qty and done_pct:
            remaining_pct = max(0.0, 100.0 - done_pct)
            elapsed_days = (today - order.start_date).days if order.start_date else 10
            elapsed_days = max(elapsed_days, 1)
            days_needed = (remaining_pct / done_pct) * elapsed_days if done_pct else 15
        else:
            days_needed = 15

        predicted_date = fields.Date.add(today, days=int(round(days_needed)))

        if order.deadline:
            risk = 'high' if predicted_date > order.deadline else \
                   ('medium' if fields.Date.add(predicted_date, days=-2) > order.deadline else 'low')
        else:
            risk = 'low'

        insight = ('Based on current progress (%.1f%% packed) and elapsed schedule, estimated completion '
                   'is %s with %s delay risk.') % (done_pct, predicted_date, risk)
        return predicted_date, risk, insight

    def predict_machine_maintenance(self, machine):
        """Return (risk, note) using running/breakdown hours as a
        deterministic proxy for predictive maintenance."""
        running = machine.running_hours_total or 0.0
        breakdown = machine.breakdown_hours_total or 0.0
        ratio = (breakdown / running) if running else 0.0

        if ratio > 0.05 or machine.status == 'breakdown':
            risk = 'high'
            note = 'Frequent breakdowns detected relative to running time. Maintenance recommended soon.'
        elif ratio > 0.02 or running > 2000:
            risk = 'medium'
            note = 'Moderate breakdown ratio / high running hours. Schedule preventive maintenance.'
        else:
            risk = 'low'
            note = 'Machine operating within normal parameters.'
        return risk, note

    def detect_line_bottleneck(self, line_balancing):
        """Return a suggestion string for the given garment.line.balancing
        record based on its operation load lines."""
        lines = line_balancing.operation_line_ids
        bottlenecks = lines.filtered('is_bottleneck')
        if not bottlenecks:
            return 'No significant bottleneck detected; line appears balanced.'
        names = ', '.join(bottlenecks.mapped('operation_name'))
        return 'Bottleneck detected at: %s. Consider adding operators or redistributing workload.' % names
