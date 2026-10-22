# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with the AI Costing
Assistant (SRS section 20 / 43): cost prediction from historical styles,
cost optimization suggestions, and buyer price/negotiation range
prediction. Rule-based and transparent, degrades gracefully without any
external AI provider configured.
"""
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineCostingExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Cost Prediction
    # ------------------------------------------------------------------
    def predict_costing(self, costing):
        if not costing.product_category_id:
            return 'No product category on the linked Style — cannot compare against historical costings.'

        history = self.env['garment.costing'].search([
            ('product_category_id', '=', costing.product_category_id.id),
            ('id', '!=', costing.id),
            ('fob_price', '>', 0),
            ('status', 'in', ('approved', 'closed')),
        ], limit=100)
        if not history:
            return ('No historical approved costings yet for this product category — prediction will improve '
                    'as more costings are approved.')

        avg_fob = sum(history.mapped('fob_price')) / len(history)
        avg_material = sum(history.mapped('material_cost')) / len(history)
        avg_cm = sum(history.mapped('cm_cost')) / len(history)

        note = ('Based on %d comparable approved costing(s): average FOB %.2f, average material cost %.2f, '
                'average CM %.2f (currency: %s).') % (
                    len(history), avg_fob, avg_material, avg_cm, costing.currency_id.name or '')
        if costing.fob_price and abs(costing.fob_price - avg_fob) / avg_fob > 0.20:
            note += (' Current FOB (%.2f) differs from the historical average by more than 20%% — '
                      'worth a second look.' % costing.fob_price)
        return note

    # ------------------------------------------------------------------
    # AI Cost Optimization
    # ------------------------------------------------------------------
    def suggest_costing_optimization(self, costing):
        suggestions = []

        if costing.bom_id:
            for alt in costing.bom_id.alternative_ids:
                if alt.cost_difference and alt.cost_difference < 0:
                    suggestions.append('Alternative material "%s" (vs "%s") saves %.2f per unit and is on file '
                                        'for this BOM.' % (alt.alternative_material, alt.main_material,
                                                            abs(alt.cost_difference)))

        recommended = costing.price_history_ids.filtered(lambda p: p.is_recommended)
        for rec_price in recommended:
            suggestions.append('Supplier "%s" is recommended for "%s" at %.2f (best price/quality/delivery '
                                'balance on file).' % (
                                    rec_price.supplier_id.name, rec_price.material_reference, rec_price.current_price))

        if costing.cm_cost and costing.material_cost and costing.cm_cost > costing.material_cost * 0.5:
            suggestions.append('CM cost is unusually high relative to material cost (>50%%) — review labor/'
                                'machine/overhead breakdown for inefficiencies.')

        if costing.additional_cost_total and costing.fob_price and (
                costing.additional_cost_total / costing.fob_price) > 0.1:
            suggestions.append('Additional costs (testing/inspection/freight/commission/bank charge) exceed '
                                '10%% of FOB — review for consolidation opportunities.')

        return '\n'.join('- %s' % s for s in suggestions) if suggestions else 'No obvious cost optimization opportunities detected.'

    # ------------------------------------------------------------------
    # AI Buyer Price Prediction / Negotiation Range
    # ------------------------------------------------------------------
    def predict_buyer_price_range(self, costing):
        if not costing.buyer_id:
            return 'No buyer linked — cannot predict a negotiation range.'

        history = self.env['garment.costing'].search([
            ('buyer_id', '=', costing.buyer_id.id),
            ('id', '!=', costing.id),
            ('status', 'in', ('approved', 'closed')),
            ('fob_price', '>', 0),
        ], limit=50)

        floor_price = costing.fob_price * 0.95 if costing.fob_price else None  # do not go below 95% of our FOB
        if not history:
            if floor_price:
                return ('No prior approved costing history for this buyer. Suggested negotiation floor: %.2f '
                        '(95%% of current FOB %.2f) — do not concede below this without management approval.' % (
                            floor_price, costing.fob_price))
            return 'No prior costing history for this buyer, and no FOB price computed yet.'

        avg_fob = sum(history.mapped('fob_price')) / len(history)
        note = 'This buyer has %d prior approved costing(s), average FOB %.2f %s.' % (
            len(history), avg_fob, costing.currency_id.name or '')
        if floor_price:
            note += ' Suggested negotiation range: %.2f (floor, 95%% of current FOB) to %.2f (current FOB).' % (
                floor_price, costing.fob_price)
        return note

    # ------------------------------------------------------------------
    # AI Cost Saving Analysis (SRS section 26)
    # ------------------------------------------------------------------
    def suggest_cost_saving(self, costing):
        """Identify Material / Production / Supplier saving opportunities and
        return (note, expected_saving_per_unit, annual_saving_estimate)."""
        notes = []
        saving_per_unit = 0.0

        # Supplier Saving: a cheaper supplier already on file for the same material reference
        for hist in costing.price_history_ids:
            cheaper = costing.price_history_ids.filtered(
                lambda p, hist=hist: p.material_reference == hist.material_reference and p.id != hist.id
                and p.current_price and hist.current_price and p.current_price < hist.current_price)
            if cheaper:
                best = min(cheaper, key=lambda p: p.current_price)
                diff = hist.current_price - best.current_price
                notes.append('Supplier Saving: switch "%s" from "%s" (%.2f) to "%s" (%.2f) - saves %.2f/unit.' % (
                    hist.material_reference, hist.supplier_id.name, hist.current_price,
                    best.supplier_id.name, best.current_price, diff))
                saving_per_unit += diff

        # Material Saving: a cheaper alternative material already on file on the linked BOM
        if costing.bom_id:
            for alt in costing.bom_id.alternative_ids.filtered(lambda a: a.cost_difference and a.cost_difference < 0):
                notes.append('Material Saving: alternative "%s" saves %.2f/unit vs "%s".' % (
                    alt.alternative_material, abs(alt.cost_difference), alt.main_material))
                saving_per_unit += abs(alt.cost_difference)

        # Production Saving: CM disproportionately high vs material cost hints at an SMV/efficiency opportunity
        if costing.cm_cost and costing.material_cost and costing.cm_cost > costing.material_cost * 0.5:
            notes.append('Production Saving: CM cost is high relative to material cost (>50%%) - review SMV/line '
                          'efficiency for a potential saving.')

        annual_saving = saving_per_unit * (costing.order_quantity or 0)
        note = '\n'.join('- %s' % n for n in notes) if notes else 'No cost saving opportunity detected yet.'
        if saving_per_unit:
            note += '\n\nEstimated Saving: %.2f/unit (Annual Estimate at current order qty: %.2f).' % (
                saving_per_unit, annual_saving)
        return note, saving_per_unit, annual_saving
