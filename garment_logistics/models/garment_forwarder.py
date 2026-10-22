# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentForwarder(models.Model):
    """Freight Forwarder Management (SRS section 13) and Carrier
    Performance Management (SRS section 45) — garment.forwarder."""
    _name = 'garment.forwarder'
    _description = 'Garment Freight Forwarder'
    _order = 'name'

    name = fields.Char(string='Company Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Related Contact')
    contact_person = fields.Char(string='Contact Person')
    address = fields.Char(string='Address')
    service_type = fields.Selection([
        ('sea_freight', 'Sea Freight'), ('air_freight', 'Air Freight'),
        ('road_freight', 'Road Freight'), ('multimodal', 'Multimodal'),
    ], string='Service Type')
    agreement_reference = fields.Char(string='Agreement Reference')
    agreement_start = fields.Date(string='Agreement Start')
    agreement_end = fields.Date(string='Agreement End')
    performance_rating = fields.Float(string='Performance Rating (%)')
    active = fields.Boolean(default=True)

    # Carrier Performance Management KPIs (SRS section 45)
    damage_rate = fields.Float(string='Damage Rate (%)')
    avg_response_time_hours = fields.Float(string='Avg. Response Time (hours)')
    performance_grade = fields.Selection([
        ('excellent', 'Excellent'), ('good', 'Good'), ('average', 'Average'), ('poor', 'Poor'),
    ], string='Rating', compute='_compute_performance_grade', store=True)

    @api.depends('performance_rating')
    def _compute_performance_grade(self):
        for rec in self:
            rating = rec.performance_rating or 0.0
            if rating >= 90:
                rec.performance_grade = 'excellent'
            elif rating >= 75:
                rec.performance_grade = 'good'
            elif rating >= 50:
                rec.performance_grade = 'average'
            else:
                rec.performance_grade = 'poor'
