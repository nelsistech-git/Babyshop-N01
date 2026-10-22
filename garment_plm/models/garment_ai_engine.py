# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (defined in garment_buyer_crm) with PLM
Development Risk / Production Readiness insight (SRS sections 39-41,
52-54: AI Product Development Assistant, AI Tech Pack Validation, AI
Production Risk Detection). Kept provider-agnostic and safe by default:
without an external AI provider configured, the analysis falls back to a
deterministic rule-based scorer built from the project's own stage-gate,
task and cross-module status data, so the feature always works.
"""
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineProjectExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    def analyze_plm_project_risk(self, project):
        """Return (risk_level: 'low'/'medium'/'high', insight: str) for a
        garment.plm.project record."""
        provider = self._get_param('garment_ai.provider', 'none')
        risk_level, insight = self._analyze_plm_project_fallback(project)
        if provider and provider != 'none':
            insight += (' (Scored using rule-based development-risk analysis; connect an AI provider '
                        'for higher-confidence trend/cost/risk recommendations.)')
        return risk_level, insight

    def _analyze_plm_project_fallback(self, project):
        from odoo import fields as _fields

        reasons = []
        score = 0
        today = _fields.Date.context_today(project)

        delayed = project.delayed_stage_count
        if delayed:
            score += min(40, delayed * 15)
            reasons.append('%d stage(s) currently delayed against their SLA target date' % delayed)

        pending_approvals = project.pending_gate_approval_count
        if pending_approvals:
            score += min(20, pending_approvals * 5)
            reasons.append('%d gate sign-off(s) awaiting approval' % pending_approvals)

        overdue_tasks = project.task_ids.filtered(
            lambda t: t.status not in ('completed', 'cancelled') and t.due_date and t.due_date < today)
        if overdue_tasks:
            score += min(20, len(overdue_tasks) * 5)
            reasons.append('%d open task(s) past their due date' % len(overdue_tasks))

        if project.techpack_id and project.techpack_status and project.techpack_status != 'approved':
            score += 5
            reasons.append('linked Tech Pack is not yet approved')
        if project.sample_id and project.sample_status and project.sample_status not in (
                'approved', 'bulk_production'):
            score += 5
            reasons.append('linked Sample is not yet buyer-approved')
        if project.target_launch_date and project.target_launch_date < today and project.state not in (
                'completed', 'cancelled'):
            score += 15
            reasons.append('target production-ready date has already passed')

        score = max(0, min(100, score))

        if score >= 50:
            risk_level = 'high'
        elif score >= 20:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        if reasons:
            insight = 'Production risk: %s. Factors: %s.' % (risk_level.upper(), '; '.join(reasons))
        else:
            insight = 'Production risk: LOW. No stage delays, no overdue tasks and no pending gate ' \
                      'sign-offs detected — project is tracking on schedule.'
        return risk_level, insight
