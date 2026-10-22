# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentOrderRisk(models.Model):
    """Order Risk Management + AI Order Risk Prediction (SRS sections 18-19,
    46) - garment.order.risk. Material / Production / Buyer / Shipment risk
    factors, manually logged or raised by the AI Order Risk Prediction
    engine.
    """
    _name = 'garment.order.risk'
    _description = 'Garment Order Risk Factor'
    _order = 'order_id, identified_date desc, id desc'

    order_id = fields.Many2one('garment.order', string='Order', required=True, ondelete='cascade')

    risk_category = fields.Selection([
        ('material', 'Material Risk'), ('production', 'Production Risk'),
        ('buyer', 'Buyer Risk'), ('shipment', 'Shipment Risk'),
    ], string='Risk Category', required=True)
    risk_factor = fields.Char(string='Risk Factor',
                               help='e.g. Fabric unavailable, Trim delay, Capacity shortage, Low efficiency, '
                                    'Late approval, Production delay, Port delay.')
    risk_score = fields.Float(string='Risk Score (%)')
    risk_level = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], string='Risk Level', default='low')
    source = fields.Selection([('manual', 'Manual'), ('ai', 'AI Prediction')], string='Source', default='manual')
    reason = fields.Text(string='Reason')
    recommendation = fields.Text(string='Recommendation')
    identified_date = fields.Date(string='Identified Date', default=fields.Date.context_today)
    resolved = fields.Boolean(string='Resolved')
    resolved_date = fields.Date(string='Resolved Date')
