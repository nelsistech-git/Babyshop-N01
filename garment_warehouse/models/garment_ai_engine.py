# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with AI Inventory
Intelligence (SRS sections 50-51): reorder point suggestion reading live
BOM demand (Module 5) and purchase forecasts (Module 9), slow-moving
stock detection, and putaway location suggestion. Rule-based,
transparent, degrades gracefully.
"""
import logging
from datetime import date

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineWarehouseExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Reorder Suggestion (SRS section 50 - Demand Forecasting)
    # ------------------------------------------------------------------
    def suggest_material_reorder(self, material):
        notes = []
        if material.stock_status == 'out_of_stock':
            notes.append('Material is OUT OF STOCK — raise a purchase requisition immediately.')
        elif material.stock_status == 'low_stock':
            notes.append('On-hand (%.1f %s) is below minimum stock (%.1f) — reorder recommended.' % (
                material.on_hand_qty, material.uom, material.minimum_stock))

        # Cross-reference open BOM demand for fabrics matching this material by name (best-effort).
        if material.category == 'fabric':
            fabric_lines = self.env['garment.fabric.bom'].search([
                ('bom_id.status', 'not in', ('closed',)),
                ('composition', 'ilike', material.name),
            ], limit=20)
            open_demand = sum(fabric_lines.mapped('required_qty'))
            if open_demand > material.available_qty:
                shortfall = open_demand - material.available_qty
                notes.append('Open BOM demand (%.1f) exceeds available stock (%.1f) — shortfall of %.1f %s.' % (
                    open_demand, material.available_qty, shortfall, material.uom))

        forecasts = self.env['garment.purchase.forecast'].search([
            ('material_name', 'ilike', material.name),
        ], limit=5, order='forecast_period desc')
        if forecasts:
            notes.append('%d recent purchase forecast(s) on file for this material — review before ordering.' % len(forecasts))

        if not notes:
            return 'Stock level is normal — no reorder action suggested.'
        return '\n'.join('- %s' % n for n in notes)

    # ------------------------------------------------------------------
    # AI Slow-Moving Detection (SRS section 38)
    # ------------------------------------------------------------------
    def detect_slow_moving_material(self, material):
        if not material.last_movement_date:
            return 'No movement history on file — cannot assess.'
        days_idle = (date.today() - material.last_movement_date).days
        if days_idle >= 240:
            return ('No movement in %d days (8+ months) — slow-moving. Suggestion: offer for a discount '
                    'order, alternate style consumption, or write-down review.') % days_idle
        elif days_idle >= 90:
            return 'No movement in %d days (90+ days) — monitor for slow-moving status.' % days_idle
        return 'Recent movement activity (%d days ago) — not slow-moving.' % days_idle

    # ------------------------------------------------------------------
    # AI Putaway Location Suggestion (SRS section 12)
    # ------------------------------------------------------------------
    def suggest_putaway_location(self, material, warehouse):
        category_warehouse_map = {
            'fabric': 'raw_material', 'yarn': 'raw_material', 'accessories': 'accessories',
            'chemical': 'chemical', 'spare_parts': 'spare_parts', 'finished_goods': 'finished_goods',
            'packaging': 'accessories',
        }
        expected_type = category_warehouse_map.get(material.category)
        if warehouse.warehouse_type != expected_type:
            return ('This material is usually stored in a "%s" warehouse, but "%s" is a "%s" warehouse — '
                    'double-check before putaway.') % (expected_type, warehouse.name, warehouse.warehouse_type)

        locations = self.env['garment.location'].search([('warehouse_id', '=', warehouse.id)], limit=1)
        if locations:
            return 'Suggested location: %s (first available location in the matching warehouse).' % locations.location_code
        return 'Warehouse type matches, but no locations are defined yet in "%s".' % warehouse.name
