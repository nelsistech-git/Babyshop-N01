# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. See LICENSE file for full copyright
# and licensing details. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentLeadSource(models.Model):
    """Configurable lead source master with cost / ROI / conversion tracking."""
    _name = 'garment.lead.source'
    _description = 'Garment Buyer Lead Source'
    _order = 'sequence, name'

    name = fields.Char(string='Lead Source', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Very High'),
    ], string='Priority', default='1')

    cost_amount = fields.Monetary(string='Cost Incurred', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # FIXED: Added store=True to match other fields using the same compute method
    lead_count = fields.Integer(string='Leads Generated', compute='_compute_conversion_stats', store=True)
    won_count = fields.Integer(string='Buyers Won', compute='_compute_conversion_stats', store=True)
    conversion_rate = fields.Float(string='Conversion Rate (%)', compute='_compute_conversion_stats', digits=(5, 2), store=True)
    roi = fields.Float(string='ROI (%)', compute='_compute_conversion_stats', digits=(5, 2), store=True)

    buyer_ids = fields.One2many('garment.buyer', 'lead_source_id', string='Buyers')

    @api.depends('buyer_ids', 'buyer_ids.buyer_status', 'cost_amount')
    def _compute_conversion_stats(self):
        for rec in self:
            leads = len(rec.buyer_ids)
            won = len(rec.buyer_ids.filtered(lambda b: b.buyer_status in ('confirmed', 'active')))
            rec.lead_count = leads
            rec.won_count = won
            rec.conversion_rate = (won / leads * 100.0) if leads else 0.0
            total_revenue = sum(rec.buyer_ids.mapped('annual_purchase_volume'))
            rec.roi = ((total_revenue - rec.cost_amount) / rec.cost_amount * 100.0) if rec.cost_amount else 0.0