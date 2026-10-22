# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with AI Financial
Intelligence (SRS sections 52-54): receivable/cash-flow risk prediction,
budget variance alerts, and LC realization risk assessment. Rule-based,
transparent, degrades gracefully.
"""
import logging
from datetime import date

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineFinanceExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Cash Flow / Receivable Risk (SRS section 52)
    # ------------------------------------------------------------------
    def predict_receivable_risk(self, buyer):
        receivables = self.env['garment.receivable'].search([
            ('buyer_id', '=', buyer.id), ('status', '!=', 'received'),
        ])
        if not receivables:
            return 'No outstanding receivables for this buyer.'

        overdue = receivables.filtered(lambda r: r.aging_bucket not in ('current',))
        total_outstanding = sum(receivables.mapped('outstanding_amount'))
        note = 'Total outstanding: %.2f across %d invoice(s).' % (total_outstanding, len(receivables))
        if overdue:
            worst = max(overdue.mapped('aging_days'))
            note += ('\n- %d invoice(s) overdue (up to %d days) — follow up with buyer before extending '
                     'further credit.') % (len(overdue), worst)
        return note

    # ------------------------------------------------------------------
    # AI Budget Variance Alert (SRS section 53 - Cost Optimization)
    # ------------------------------------------------------------------
    def suggest_budget_action(self, budget):
        if not budget.budgeted_amount:
            return 'No budgeted amount set — cannot assess variance.'
        if budget.utilization_pct >= 100:
            return ('Budget fully consumed or exceeded (%.0f%% utilized) — review remaining commitments '
                    'and consider a supplementary budget request.') % budget.utilization_pct
        elif budget.utilization_pct >= 85:
            return 'Budget is %.0f%% utilized — approaching limit, monitor closely.' % budget.utilization_pct
        today = date.today()
        if budget.period_end and budget.period_end < today and budget.utilization_pct < 50:
            return ('Budget period has ended with only %.0f%% utilized — review whether planned spend was '
                    'deferred or the budget was overestimated.') % budget.utilization_pct
        return 'Budget utilization (%.0f%%) is within normal range.' % budget.utilization_pct

    # ------------------------------------------------------------------
    # AI LC Realization Risk (SRS section 54 - Profit Forecasting area)
    # ------------------------------------------------------------------
    def predict_lc_realization_risk(self, lc):
        score = 0
        reasons = []
        today = date.today()

        if lc.expiry_date and lc.expiry_date < today and lc.status not in ('utilized',):
            score += 40
            reasons.append('LC expiry date (%s) has passed and LC is not yet marked utilized.' % lc.expiry_date)
        elif lc.expiry_date and (lc.expiry_date - today).days <= 15 and lc.workflow_stage not in (
                'export_documents', 'payment_received'):
            score += 25
            reasons.append('LC expires within 15 days but workflow is still at "%s" stage.' % lc.workflow_stage)

        if lc.shipment_deadline and lc.shipment_deadline < today and lc.workflow_stage in (
                'buyer_order', 'lc_received', 'lc_verification', 'bank_approval', 'material_procurement',
                'production'):
            score += 30
            reasons.append('Shipment deadline (%s) has passed but shipment has not started.' % lc.shipment_deadline)

        required_docs = {'lc_copy', 'invoice', 'packing_list', 'bl_copy'}
        have_docs = set(lc.document_ids.filtered('is_submitted').mapped('document_type'))
        missing = required_docs - have_docs
        if lc.workflow_stage in ('export_documents', 'payment_received') and missing:
            score += 20
            reasons.append('Missing submitted document(s) for bank negotiation: %s.' % ', '.join(sorted(missing)))

        if lc.amendment_count and lc.amendment_count >= 3:
            score += 10
            reasons.append('LC has been amended %d times — verify latest terms are fully reflected.' %
                            lc.amendment_count)

        score = max(0, min(100, score))
        level = 'HIGH' if score >= 50 else 'MEDIUM' if score >= 25 else 'LOW'
        note = 'LC Realization Risk: %s (score %d/100).' % (level, score)
        if reasons:
            note += '\n' + '\n'.join('- %s' % r for r in reasons)
        else:
            note += '\nNo significant risk factors detected.'
        return note

    # ------------------------------------------------------------------
    # AI Cash Flow Prediction (SRS section 45, Module 20 / section 52,
    # Module 37) — predicts future cash shortage for a
    # garment.cash.flow.forecast record.
    # ------------------------------------------------------------------
    def predict_cash_flow_risk(self, forecast):
        if forecast.closing_balance < 0:
            level = 'HIGH'
        elif forecast.expected_outflow > (forecast.opening_balance + forecast.expected_inflow) * 0.7:
            level = 'MEDIUM'
        else:
            level = 'LOW'

        reasons = []
        if forecast.expected_outflow > forecast.expected_inflow:
            reasons.append('Expected outflow (%.2f) exceeds expected inflow (%.2f) for the period.' % (
                forecast.expected_outflow, forecast.expected_inflow))
        if forecast.closing_balance < 0:
            reasons.append('Projected closing balance is negative (%.2f) — a cash shortage is expected.' %
                            forecast.closing_balance)

        note = 'Cash Flow Risk: %s.' % level
        if reasons:
            note += '\n' + '\n'.join('- %s' % r for r in reasons)
            note += '\nRecommendation: Accelerate buyer collection and/or defer non-critical supplier payments.'
        else:
            note += '\nNo significant cash shortage risk detected for this period.'
        return note
