# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentBomPriceHistory(models.Model):
    """Material Price History (SRS section 22) — garment.bom.price.history.
    One row per price change on a Supplier Mapping line, auto-logged by
    garment.bom.supplier so Price Trend / Cost Increase Analysis reporting
    has real historical data to work from."""
    _name = 'garment.bom.price.history'
    _description = 'Garment Material Price History'
    _order = 'effective_date desc, id desc'

    bom_supplier_id = fields.Many2one('garment.bom.supplier', string='Supplier Mapping',
                                       required=True, ondelete='cascade')
    material_reference = fields.Char(related='bom_supplier_id.material_reference', store=True)
    supplier_id = fields.Many2one(related='bom_supplier_id.supplier_id', store=True)
    bom_id = fields.Many2one(related='bom_supplier_id.bom_id', store=True)
    currency_id = fields.Many2one(related='bom_supplier_id.currency_id', store=True)
    previous_price = fields.Monetary(string='Previous Price', currency_field='currency_id')
    current_price = fields.Monetary(string='Current Price', currency_field='currency_id')
    price_change_pct = fields.Float(string='Change %', compute='_compute_change_pct', store=True)
    effective_date = fields.Date(string='Effective Date', default=fields.Date.context_today)
    changed_by_id = fields.Many2one('res.users', string='Changed By')
    reason = fields.Char(string='Reason')

    def _compute_change_pct(self):
        for rec in self:
            rec.price_change_pct = (
                (rec.current_price - rec.previous_price) / rec.previous_price * 100.0
                if rec.previous_price else 0.0)
