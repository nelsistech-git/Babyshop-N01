# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with the AI BOM Assistant
(SRS section 26): starting-BOM suggestion from the linked Style, fabric
consumption prediction from historical BOMs, and cost optimization
suggestions. All rule-based and fully transparent — degrades gracefully,
never blocks the BOM workflow.
"""
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineBomExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # Auto BOM Creation suggestion
    # ------------------------------------------------------------------
    def suggest_bom_from_style(self, bom):
        style = bom.style_id
        if not style:
            return 'No style linked — cannot suggest a starting BOM.'
        fabric_count = len(style.fabric_line_ids)
        trim_count = len(style.trim_line_ids)
        already_fabric = len(bom.fabric_bom_ids)
        already_trim = len(bom.trim_bom_ids)
        if not fabric_count and not trim_count:
            return ('The linked Style has no fabric or trim specification lines yet — add them on the '
                    'Style record, or fill in the BOM manually.')
        lines = []
        if fabric_count and not already_fabric:
            lines.append('%d fabric line(s) available on the Style — use "Import From Style" to copy them '
                          'into this BOM as a starting point.' % fabric_count)
        if trim_count and not already_trim:
            lines.append('%d trim line(s) available on the Style — use "Import From Style" to copy them '
                          'into this BOM as a starting point.' % trim_count)
        if not lines:
            lines.append('Fabric/trim lines already present on this BOM (or nothing new to import).')
        return '\n'.join('- %s' % l for l in lines)

    # ------------------------------------------------------------------
    # Consumption Prediction
    # ------------------------------------------------------------------
    def predict_bom_consumption(self, bom):
        if not bom.style_category_id:
            return 'No product category set on the linked Style — cannot compare against historical BOMs.'

        historical_fabrics = self.env['garment.fabric.bom'].search([
            ('bom_id.style_category_id', '=', bom.style_category_id.id),
            ('bom_id', '!=', bom.id),
            ('net_consumption', '>', 0),
        ], limit=200)
        if not historical_fabrics:
            return 'No historical fabric BOM data yet for this product category — prediction will improve as more BOMs are approved.'

        by_role = {}
        for f in historical_fabrics:
            by_role.setdefault(f.fabric_role, []).append(f.net_consumption)

        lines = []
        for line in bom.fabric_bom_ids:
            history = by_role.get(line.fabric_role)
            if not history:
                continue
            avg = sum(history) / len(history)
            if line.net_consumption and abs(line.net_consumption - avg) / avg > 0.15:
                lines.append('%s: entered %.3f vs historical average %.3f (%d samples) — variance over 15%%, please double-check.' % (
                    line.fabric_role, line.net_consumption, avg, len(history)))
        if not lines:
            return ('Consumption values are in line with historical averages for this product category '
                    '(%d comparable fabric lines analyzed).') % len(historical_fabrics)
        return 'Consumption variances detected:\n' + '\n'.join('- %s' % l for l in lines)

    # ------------------------------------------------------------------
    # Cost Optimization
    # ------------------------------------------------------------------
    def suggest_bom_cost_optimization(self, bom):
        suggestions = []

        for fabric in bom.fabric_bom_ids:
            if fabric.total_wastage_pct and fabric.total_wastage_pct > 15:
                suggestions.append('Fabric "%s": total wastage %.1f%% is high — review cutting/marker efficiency.' % (
                    fabric.fabric_role, fabric.total_wastage_pct))

        material_refs = bom.supplier_ids.mapped('material_reference')
        for ref in set(material_refs):
            suppliers = bom.supplier_ids.filtered(lambda s, r=ref: s.material_reference == r)
            if len(suppliers) > 1:
                cheapest = min(suppliers, key=lambda s: s.current_price or float('inf'))
                current = suppliers.filtered(lambda s: s.supplier_type == 'factory_approved')[:1]
                if current and current.current_price and cheapest.current_price and cheapest != current[0] \
                        and cheapest.current_price < current[0].current_price:
                    savings = current[0].current_price - cheapest.current_price
                    suggestions.append('Material "%s": supplier "%s" offers a lower price (saving %.2f/unit) '
                                        'than the current factory-approved supplier.' % (
                                            ref, cheapest.supplier_id.name, savings))

        if bom.cost_per_piece and bom.target_cost and bom.cost_per_piece > bom.target_cost:
            over = bom.cost_per_piece - bom.target_cost
            suggestions.append('Cost per piece (%.2f) exceeds target cost (%.2f) by %.2f — review high-cost lines.' % (
                bom.cost_per_piece, bom.target_cost, over))

        return '\n'.join('- %s' % s for s in suggestions) if suggestions else 'No obvious cost optimization opportunities detected.'

    # ------------------------------------------------------------------
    # AI Risk Detection (SRS section 44) — material shortage, supplier
    # delay, price increase and production impact risk.
    # ------------------------------------------------------------------
    def suggest_bom_risk_detection(self, bom):
        risks = []

        for res in bom.reservation_ids.filtered(lambda r: r.shortage_qty > 0):
            risks.append('Material shortage risk: "%s" short by %.2f (Order %s).' % (
                res.material_name or res.material_type, res.shortage_qty, res.order_reference or '-'))

        for sup in bom.supplier_ids.filtered(lambda s: s.lead_time_days and s.lead_time_days > 30):
            risks.append('Supplier delay risk: "%s" for "%s" has a long lead time (%d days).' % (
                sup.supplier_id.name, sup.material_reference, sup.lead_time_days))

        for sup in bom.supplier_ids:
            recent = sup.price_history_ids.sorted('effective_date', reverse=True)[:1]
            if recent and recent.price_change_pct and recent.price_change_pct > 10:
                risks.append('Price increase risk: "%s" from "%s" rose %.1f%% on %s.' % (
                    sup.material_reference, sup.supplier_id.name, recent.price_change_pct, recent.effective_date))

        if bom.material_availability_pct and bom.material_availability_pct < 100 and bom.reservation_ids:
            risks.append('Production impact risk: material availability at %.0f%% — production start may be delayed.' % (
                bom.material_availability_pct))

        return '\n'.join('- %s' % r for r in risks) if risks else 'No material, supplier or price risks detected.'
