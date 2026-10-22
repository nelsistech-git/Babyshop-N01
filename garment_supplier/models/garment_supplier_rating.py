# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentSupplierRating(models.Model):
    """Supplier Performance Management + Rating System + Scorecard
    (SRS sections 16-17, 42-43) — garment.supplier.rating.
    Score = Quality 40% + Delivery 30% + Cost 20% + Compliance 10%."""
    _name = 'garment.supplier.rating'
    _description = 'Garment Supplier Rating'
    _order = 'rating_date desc'

    supplier_id = fields.Many2one('garment.supplier', string='Supplier', required=True, ondelete='cascade')
    rating_date = fields.Date(string='Rating Date', default=fields.Date.context_today, required=True)
    rated_by_id = fields.Many2one('res.users', string='Rated By', default=lambda s: s.env.user)

    # Quality Performance
    rejection_rate_pct = fields.Float(string='Rejection Rate %')
    defect_rate_pct = fields.Float(string='Defect Rate %')
    quality_score = fields.Float(string='Quality Score (%)')

    # Delivery Performance
    on_time_delivery_pct = fields.Float(string='On-Time Delivery %')
    avg_delay_days = fields.Float(string='Average Delay Days')
    lead_time_accuracy_pct = fields.Float(string='Lead Time Accuracy %')
    delivery_score = fields.Float(string='Delivery Score (%)')

    # Cost Performance
    price_stability_score = fields.Float(string='Price Stability Score (%)')
    cost_competitiveness_score = fields.Float(string='Cost Competitiveness Score (%)')
    cost_score = fields.Float(string='Cost Score (%)', compute='_compute_cost_score', store=True)

    # Compliance Performance
    compliance_score = fields.Float(string='Compliance Score (%)')

    final_score = fields.Float(string='Final Score (%)', compute='_compute_final_score', store=True)
    star_rating = fields.Selection([
        ('5', '★★★★★ Excellent'), ('4', '★★★★ Good'), ('3', '★★★ Average'),
        ('2', '★★ Poor'), ('1', '★ Critical'),
    ], string='Star Rating', compute='_compute_final_score', store=True)
    notes = fields.Text(string='Notes')

    @api.depends('price_stability_score', 'cost_competitiveness_score')
    def _compute_cost_score(self):
        for rec in self:
            rec.cost_score = ((rec.price_stability_score or 0.0) + (rec.cost_competitiveness_score or 0.0)) / 2.0

    @api.depends('quality_score', 'delivery_score', 'cost_score', 'compliance_score')
    def _compute_final_score(self):
        for rec in self:
            score = (rec.quality_score * 0.40 + rec.delivery_score * 0.30
                     + rec.cost_score * 0.20 + rec.compliance_score * 0.10)
            rec.final_score = score
            if score >= 90:
                rec.star_rating = '5'
            elif score >= 75:
                rec.star_rating = '4'
            elif score >= 60:
                rec.star_rating = '3'
            elif score >= 40:
                rec.star_rating = '2'
            else:
                rec.star_rating = '1'
