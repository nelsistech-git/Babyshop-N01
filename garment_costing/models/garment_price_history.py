# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentPriceHistory(models.Model):
    """Supplier Price Integration (SRS section 23) — garment.price.history."""
    _name = 'garment.price.history'
    _description = 'Garment Supplier Price History'
    _order = 'sequence'

    costing_id = fields.Many2one('garment.costing', string='Costing', ondelete='cascade')
    sequence = fields.Integer(default=10)
    material_reference = fields.Char(string='Material', required=True)
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True)
    previous_price = fields.Monetary(string='Previous Price', currency_field='currency_id')
    current_price = fields.Monetary(string='Current Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    moq = fields.Float(string='MOQ')
    lead_time_days = fields.Integer(string='Lead Time (days)')
    validity_period = fields.Date(string='Validity Period')
    quality_rating = fields.Selection([
        ('1', '1 - Poor'), ('2', '2 - Fair'), ('3', '3 - Good'), ('4', '4 - Very Good'), ('5', '5 - Excellent'),
    ], string='Quality Rating')
    delivery_rating = fields.Selection([
        ('1', '1 - Poor'), ('2', '2 - Fair'), ('3', '3 - Good'), ('4', '4 - Very Good'), ('5', '5 - Excellent'),
    ], string='Delivery Rating')
    compliance_ok = fields.Boolean(string='Compliance OK')
    is_recommended = fields.Boolean(string='Recommended Supplier', compute='_compute_recommended', store=True)

    @api.depends('current_price', 'quality_rating', 'delivery_rating', 'compliance_ok')
    def _compute_recommended(self):
        for rec in self:
            # Recommend suppliers priced within 5% of the cheapest for the same
            # material reference, with acceptable quality/delivery/compliance.
            siblings = self.search([
                ('material_reference', '=', rec.material_reference),
                ('costing_id', '=', rec.costing_id.id),
            ]) if rec.material_reference else rec
            cheapest = min(siblings.mapped('current_price') or [0.0]) if siblings else 0.0
            rec.is_recommended = bool(
                rec.compliance_ok and rec.current_price and cheapest
                and rec.current_price <= cheapest * 1.05
                and (rec.quality_rating or '0') >= '3'
            )
