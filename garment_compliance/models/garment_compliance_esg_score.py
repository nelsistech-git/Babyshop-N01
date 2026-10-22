# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
ESG Score Management (SRS1 secs. 41-42, 51) — garment.compliance.esg.score.
Environmental 40% + Social 40% + Governance 20% weighted score, matching
the SRS1 sec. 42 formula. Also the record the Buyer Sustainability
Portal (SRS1 sec. 51) surfaces per period.
"""
from odoo import api, fields, models


class GarmentComplianceEsgScore(models.Model):
    _name = 'garment.compliance.esg.score'
    _description = 'Garment Compliance ESG Score'
    _order = 'period_date desc'

    name = fields.Char(string='Period', required=True, help='e.g. "January 2026" or "Q1 2026".')
    period_date = fields.Date(string='Period Date', default=fields.Date.context_today, required=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', help='Set to publish a buyer-specific ESG score.')

    environmental_score = fields.Float(string='Environmental Score (%)')
    social_score = fields.Float(string='Social Score (%)')
    governance_score = fields.Float(string='Governance Score (%)')
    overall_score = fields.Float(string='Overall ESG Score (%)', compute='_compute_overall_score', store=True)

    carbon_reduction_percentage = fields.Float(string='Carbon Reduction (%)')
    water_saving_percentage = fields.Float(string='Water Saving (%)')
    waste_recycling_percentage = fields.Float(string='Waste Recycling (%)')
    notes = fields.Text(string='Notes')

    @api.depends('environmental_score', 'social_score', 'governance_score')
    def _compute_overall_score(self):
        for rec in self:
            rec.overall_score = (rec.environmental_score * 0.4) + (rec.social_score * 0.4) + (rec.governance_score * 0.2)
