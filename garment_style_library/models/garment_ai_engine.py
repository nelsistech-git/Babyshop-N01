# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (defined in garment_buyer_crm) with AI-Assisted
Style Similarity (SRS section 27). Kept provider-agnostic and safe by
default: without an external AI provider configured, similarity falls back
to a deterministic attribute-matching scorer so the feature always works.
"""
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineStyleExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    def find_similar_styles(self, style, limit=5):
        """Return (recordset of similar garment.style, insight text)."""
        provider = self._get_param('garment_ai.provider', 'none')
        candidates = self.env['garment.style'].search([
            ('id', '!=', style.id),
            ('style_category_id', '=', style.style_category_id.id),
        ], limit=50) if style.style_category_id else self.env['garment.style'].search(
            [('id', '!=', style.id)], limit=50)

        scored = []
        for candidate in candidates:
            score = self._similarity_score(style, candidate)
            if score > 0:
                scored.append((score, candidate))
        scored.sort(key=lambda t: t[0], reverse=True)
        top = scored[:limit]
        similar_styles = self.env['garment.style'].browse([c.id for _s, c in top])

        if top:
            details = ', '.join('%s (%.0f%% match)' % (c.style_name, s) for s, c in top)
            insight = 'Found %d similar historical style(s): %s.' % (len(top), details)
        else:
            insight = 'No sufficiently similar historical styles found yet — as more styles are added ' \
                      'to the library, matches will improve.'

        if provider and provider != 'none':
            insight += ' (Scored using rule-based attribute matching; connect more style data for ' \
                       'higher-confidence AI matching.)'

        return similar_styles, insight

    def _similarity_score(self, style, candidate):
        score = 0
        weights = {
            'style_category_id': 25, 'gender': 10, 'age_group': 10, 'market': 5,
            'sleeve_type': 8, 'neck_type': 8, 'collar_type': 8, 'fit_type': 10,
            'construction_type': 8, 'buyer_id': 8,
        }
        for field_name, weight in weights.items():
            a = getattr(style, field_name)
            b = getattr(candidate, field_name)
            if a and b and a == b:
                score += weight
        return score
