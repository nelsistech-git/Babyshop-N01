# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Garment AI Engine
=================
A thin, pluggable AI service layer used across the Smart Complete Garment
Software suite. Every module (Buyer CRM today, Merchandising / Quality /
Production later) calls into this single engine so that AI provider
credentials and prompt conventions live in exactly one place.

Configuration (Settings > Technical > System Parameters, or the
"AI Assist" tab on Settings once installed):
    garment_ai.provider        openai | anthropic | azure_openai | custom | none
    garment_ai.api_key         secret key for the chosen provider
    garment_ai.api_endpoint    base URL (required for azure_openai / custom)
    garment_ai.model           model name, e.g. gpt-4o-mini / claude-3-5-haiku

If no provider is configured, the engine falls back to a transparent,
deterministic rule-based scorer so the feature always works out of the box
and never blocks a fresh install on having an API key.
"""
import json
import logging
from datetime import timedelta

from odoo import fields, models, _

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover - requests ships with Odoo, kept defensive
    requests = None


class GarmentAIEngine(models.AbstractModel):
    _name = 'garment.ai.engine'
    _description = 'Garment Smart AI Engine (pluggable lead scoring & insights)'

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def score_buyer(self, buyer):
        """Return (score: float 0-100, insight: str) for a garment.buyer record."""
        provider = self._get_param('garment_ai.provider', 'none')
        if provider and provider != 'none' and requests is not None:
            try:
                return self._score_buyer_via_provider(buyer, provider)
            except Exception as exc:  # noqa: BLE001 - never let AI failures break CRM flow
                _logger.warning('Garment AI Engine: external call failed (%s), using fallback scorer.', exc)
        return self._score_buyer_fallback(buyer)

    def predict_opportunity(self, opportunity):
        """Return a dict of AI Opportunity Prediction fields (SRS section 20)
        for a garment.opportunity record. Falls back to a deterministic
        heuristic when no AI provider is configured, exactly like
        :meth:`score_buyer`."""
        return self._predict_opportunity_fallback(opportunity)

    def _predict_opportunity_fallback(self, opportunity):
        buyer = opportunity.buyer_id
        base_probability = opportunity.probability or 10.0
        score_bonus = min(30.0, (buyer.ai_lead_score or 0.0) * 0.3)
        stage_bonus = min(30.0, (opportunity.stage_id.sequence or 0) / 2.0)
        probability = max(0.0, min(100.0, base_probability + score_bonus + stage_bonus))

        expected_margin = (opportunity.estimated_order_value or 0.0) * 0.15
        response_days = 3 if buyer.buyer_status in ('active', 'confirmed') else 7

        today = fields.Date.context_today(opportunity)
        expected_po_date = opportunity.expected_order_date or (today + timedelta(days=30))
        followup_date = today + timedelta(days=3)

        if probability >= 70:
            next_action = _('Proceed to costing / send quotation follow-up.')
        elif probability >= 40:
            next_action = _('Schedule a buyer discussion to address open concerns.')
        else:
            next_action = _('Re-qualify: confirm buyer requirement and budget before investing further effort.')

        similar_orders = _('Based on %d prior opportunit%s and %d RFQ(s) on file for this buyer.') % (
            buyer.opportunity_count, 'y' if buyer.opportunity_count == 1 else 'ies', buyer.rfq_count)

        insight = _('Rule-based prediction (no AI provider configured): probability derived from buyer AI '
                     'score (%.1f) and opportunity stage progress.') % (buyer.ai_lead_score or 0.0)

        return {
            'ai_probability_win': probability,
            'ai_expected_margin': expected_margin,
            'ai_buyer_response_time_days': response_days,
            'ai_expected_po_date': expected_po_date,
            'ai_suggested_followup_date': followup_date,
            'ai_suggested_next_action': next_action,
            'ai_recommended_sales_executive_id': opportunity.sales_executive_id.id or False,
            'ai_similar_historical_orders': similar_orders,
            'ai_last_insight': insight,
        }

    # ------------------------------------------------------------------
    # External provider call (generic chat-completions style contract)
    # ------------------------------------------------------------------
    def _score_buyer_via_provider(self, buyer, provider):
        api_key = self._get_param('garment_ai.api_key')
        endpoint = self._get_param('garment_ai.api_endpoint') or self._default_endpoint(provider)
        model = self._get_param('garment_ai.model') or self._default_model(provider)
        if not api_key or not endpoint:
            return self._score_buyer_fallback(buyer)

        prompt = self._build_buyer_prompt(buyer)
        headers = {'Content-Type': 'application/json'}
        if provider == 'anthropic':
            headers['x-api-key'] = api_key
            headers['anthropic-version'] = '2023-06-01'
            payload = {
                'model': model,
                'max_tokens': 300,
                'messages': [{'role': 'user', 'content': prompt}],
            }
        else:  # openai / azure_openai / custom - OpenAI-compatible chat completions
            headers['Authorization'] = 'Bearer %s' % api_key
            payload = {
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.2,
            }

        response = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=20)
        response.raise_for_status()
        data = response.json()

        if provider == 'anthropic':
            text = ''.join(block.get('text', '') for block in data.get('content', []) if block.get('type') == 'text')
        else:
            text = data.get('choices', [{}])[0].get('message', {}).get('content', '')

        return self._parse_ai_response(text, buyer)

    def _parse_ai_response(self, text, buyer):
        try:
            parsed = json.loads(text)
            score = float(parsed.get('score', 50.0))
            insight = parsed.get('insight') or text
        except (ValueError, TypeError):
            score = self._score_buyer_fallback(buyer)[0]
            insight = text or 'AI provider returned no structured insight.'
        return max(0.0, min(100.0, score)), insight

    def _build_buyer_prompt(self, buyer):
        return (
            'You are a garment export sales analyst. Given this buyer profile, '
            'return ONLY a JSON object like {"score": <0-100 propensity to convert '
            'into a repeat, high-value buyer>, "insight": "<one sentence recommendation>"}.\n'
            'Buyer: %s | Category: %s | Type: %s | Status: %s | Annual Purchase Volume: %s %s | '
            'Country: %s | Lead Source: %s | Open Opportunities: %s | Open RFQs: %s'
        ) % (
            buyer.name, buyer.buyer_category or '-', buyer.buyer_type or '-', buyer.buyer_status,
            buyer.annual_purchase_volume, buyer.currency_id.name or '',
            buyer.country_id.name or '-', buyer.lead_source_id.name or '-',
            buyer.opportunity_count, buyer.rfq_count,
        )

    # ------------------------------------------------------------------
    # Deterministic fallback scorer (no external dependency required)
    # ------------------------------------------------------------------
    def _score_buyer_fallback(self, buyer):
        score = 20.0
        reasons = []

        status_weight = {
            'new_lead': 5, 'contacted': 10, 'meeting_scheduled': 20, 'interested': 30,
            'rfq_received': 45, 'quotation_sent': 55, 'negotiation': 65, 'sampling': 70,
            'confirmed': 90, 'active': 95, 'inactive': 15, 'blacklisted': 0,
        }
        score = status_weight.get(buyer.buyer_status, score)

        if buyer.annual_purchase_volume and buyer.annual_purchase_volume > 0:
            score += min(15, buyer.annual_purchase_volume / 100000.0)
            reasons.append('has a disclosed annual purchase volume')
        if buyer.opportunity_count:
            score += min(10, buyer.opportunity_count * 2)
            reasons.append('%d active opportunit%s' % (
                buyer.opportunity_count, 'y' if buyer.opportunity_count == 1 else 'ies'))
        if buyer.rfq_count:
            score += min(10, buyer.rfq_count * 2)
            reasons.append('%d RFQ(s) on file' % buyer.rfq_count)
        if buyer.nda_signed:
            score += 5
        if buyer.buyer_type in ('vip', 'strategic', 'key_account'):
            score += 10
            reasons.append('flagged as %s' % buyer.buyer_type)

        score = max(0.0, min(100.0, score))
        insight = 'Rule-based score (no AI provider configured). Factors: %s.' % (
            '; '.join(reasons) if reasons else 'limited profile data available — encourage the '
                                                'merchandiser to complete the buyer profile.'
        )
        return score, insight

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_param(self, key, default=None):
        return self.env['ir.config_parameter'].sudo().get_param(key, default)

    def _default_endpoint(self, provider):
        return {
            'openai': 'https://api.openai.com/v1/chat/completions',
            'anthropic': 'https://api.anthropic.com/v1/messages',
        }.get(provider)

    def _default_model(self, provider):
        return {
            'openai': 'gpt-4o-mini',
            'anthropic': 'claude-3-5-haiku-20241022',
        }.get(provider, 'gpt-4o-mini')
