# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with the AI Merchandising
Assistant: quotation price suggestion from the linked BOM cost sheet,
negotiation counter-offer suggestion, and workload-aware merchandiser
recommendation. All rule-based, transparent, and safe to run without any
external AI provider configured.
"""
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineMerchExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # Quotation price suggestion
    # ------------------------------------------------------------------
    def suggest_quotation_price(self, quotation):
        if not quotation.bom_id:
            return ('No cost sheet (BOM) linked to this quotation — link one to get a cost-based price '
                    'suggestion, or enter the price manually.')
        cost_per_piece = quotation.bom_id.cost_per_piece
        if not cost_per_piece:
            return 'Linked BOM has no computed cost per piece yet — complete the fabric/trim/packaging lines first.'

        target_margin = quotation.bom_id.profit_margin or 15.0
        suggested_price = cost_per_piece * (1 + target_margin / 100.0)

        history = self.env['garment.merch.quotation'].search([
            ('buyer_id', '=', quotation.buyer_id.id),
            ('status', '=', 'accepted'),
            ('id', '!=', quotation.id),
        ], limit=20)
        note = ('Suggested price: %.2f %s (cost/piece %.2f + %.0f%% margin).' % (
            suggested_price, quotation.currency_id.name or '', cost_per_piece, target_margin))
        if history:
            note += ' This buyer has %d prior accepted quotation(s) — review their typical price band before sending.' % len(history)
        return note

    # ------------------------------------------------------------------
    # Negotiation counter-offer suggestion
    # ------------------------------------------------------------------
    def suggest_negotiation_counter(self, negotiation):
        bom = negotiation.quotation_id.bom_id
        floor_price = bom.cost_per_piece * 1.05 if bom and bom.cost_per_piece else None  # keep >=5% margin as floor

        if not negotiation.requested_price:
            return 'No buyer requested price recorded yet — log the buyer\'s ask before requesting a suggestion.'

        if floor_price and negotiation.requested_price < floor_price:
            midpoint = (negotiation.requested_price + floor_price) / 2.0
            return ('Buyer\'s requested price (%.2f) is below the cost-safe floor (%.2f, cost + 5%% minimum '
                    'margin). Suggested counter: %.2f — explain the cost basis rather than conceding further.' % (
                        negotiation.requested_price, floor_price, midpoint))
        elif negotiation.offered_price and negotiation.requested_price:
            midpoint = (negotiation.offered_price + negotiation.requested_price) / 2.0
            return 'Suggested counter-offer (midpoint of our offer and buyer\'s ask): %.2f.' % midpoint
        return 'Not enough data (need both an offered price and the buyer\'s requested price) to suggest a counter.'

    # ------------------------------------------------------------------
    # Workload-aware merchandiser recommendation
    # ------------------------------------------------------------------
    def recommend_merchandiser_for_inquiry(self, inquiry):
        merchandisers = self.env['res.users'].search([
            ('groups_id.category_id.name', '=', 'Smart Garment ERP - Merchandising')
        ]) or self.env['garment.merch.inquiry'].search([]).mapped('assigned_merchandiser_id')

        if not merchandisers:
            return None, ('No merchandisers found to recommend from. Assign the "Merchandiser" group to at '
                           'least one user, or set the assignment manually.')

        workload = {}
        for user in merchandisers:
            open_count = self.env['garment.merch.inquiry'].search_count([
                ('assigned_merchandiser_id', '=', user.id),
                ('status', 'not in', ('order_confirmed', 'lost')),
            ])
            workload[user] = open_count

        best_user = min(workload, key=lambda u: workload[u])
        note = 'Recommended merchandiser: %s (%d open inquiries, lowest current workload among %d candidates).' % (
            best_user.name, workload[best_user], len(workload))
        return best_user, note
