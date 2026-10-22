# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentPurchaseForecast(models.Model):
    """AI Procurement Intelligence storage (SRS sections 39, 41) —
    garment.purchase.forecast. Serves three related AI outputs sharing
    the same "forecast" shape: material demand forecasts, purchase price
    predictions, and supplier delivery-delay risk predictions."""
    _name = 'garment.purchase.forecast'
    _description = 'Garment Purchase Forecast'
    _order = 'forecast_period desc'

    forecast_type = fields.Selection([
        ('demand', 'Demand Forecast'), ('price_prediction', 'Price Prediction'),
        ('delay_risk', 'Delivery Delay Risk'),
    ], string='Forecast Type', default='demand', required=True)

    material_category = fields.Selection([
        ('fabric', 'Fabric'), ('trim', 'Trim/Accessory'), ('packaging', 'Packaging'), ('other', 'Other'),
    ], string='Material Category')
    material_name = fields.Char(string='Material')
    forecast_period = fields.Date(string='Forecast Period (Month Start)', required=True)
    expected_requirement_qty = fields.Float(string='Expected Requirement Quantity')
    uom = fields.Char(string='UoM')

    # AI Purchase Price Prediction (SRS section 41)
    current_price = fields.Float(string='Current Price')
    predicted_price_change_pct = fields.Float(string='Predicted Price Change (%)')

    # AI Purchase Delay Prediction (SRS section 41)
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    risk_level = fields.Selection([('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], string='Risk Level')

    basis_note = fields.Text(string='Forecast Basis',
                              help='Orders / production plan / historical consumption used to derive this figure.')
    recommendation = fields.Text(string='Recommendation')
    confidence_pct = fields.Float(string='Confidence (%)')
    generated_date = fields.Datetime(string='Generated Date', default=fields.Datetime.now)

    requisition_id = fields.Many2one('garment.purchase.requisition', string='Requisition Raised', copy=False,
                                      readonly=True)

    def action_create_requisition(self):
        """AI Automatic Purchase Planning (SRS section 41): turn a demand
        forecast into a draft Purchase Requisition."""
        Requisition = self.env['garment.purchase.requisition']
        for rec in self:
            if rec.forecast_type != 'demand' or rec.requisition_id or rec.expected_requirement_qty <= 0:
                continue
            requisition = Requisition.create({
                'source': 'planning',
                'material_type': rec.material_category or 'other',
                'required_date': rec.forecast_period,
                'priority': 'medium',
                'line_ids': [(0, 0, {
                    'material_category': rec.material_category or 'other',
                    'material_name': rec.material_name or _('Forecasted Material'),
                    'uom': rec.uom,
                    'required_qty': rec.expected_requirement_qty,
                })],
            })
            rec.requisition_id = requisition.id
        return True

    def action_open_requisition(self):
        self.ensure_one()
        return {
            'name': _('Purchase Requisition'), 'type': 'ir.actions.act_window',
            'res_model': 'garment.purchase.requisition', 'view_mode': 'form',
            'res_id': self.requisition_id.id,
        }
