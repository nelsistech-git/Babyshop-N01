# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Supplier RFQ (SRS sections 13-15). Named garment.purchase.rfq rather than
the SRS's proposed garment.rfq, because garment.rfq already exists in
garment_buyer_crm as the BUYER-side inquiry model — a different business
object entirely (buyer asking us for a quote vs. us asking a supplier).
"""
from odoo import api, fields, models, _


class GarmentPurchaseRfq(models.Model):
    _name = 'garment.purchase.rfq'
    _description = 'Garment Supplier RFQ (Request for Quotation)'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'

    rfq_number = fields.Char(string='RFQ Number', copy=False, readonly=True, default=lambda s: _('New'))
    rfq_source = fields.Selection([
        ('approved_pr', 'Approved PR'), ('material_shortage', 'Material Shortage'),
        ('production_plan', 'Production Plan'), ('manual', 'Manual'),
    ], string='RFQ Source', default='approved_pr',
        help='Automatic RFQ Creation source (SRS section 14): Approved PR / Material shortage / '
             'Production plan, or a manually raised RFQ.')
    requisition_id = fields.Many2one('garment.purchase.requisition', string='Purchase Requisition')
    requisition_line_id = fields.Many2one('garment.purchase.request.line', string='Requisition Line')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True)
    material_name = fields.Char(string='Material', required=True)
    specification = fields.Char(string='Specification')
    quantity = fields.Float(string='Quantity')
    uom = fields.Char(string='UoM')
    delivery_date = fields.Date(string='Delivery Date')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    incoterm_id = fields.Many2one('account.incoterms', string='Incoterms')

    quotation_ids = fields.One2many('garment.supplier.quotation', 'rfq_id', string='Quotations')
    quotation_count = fields.Integer(compute='_compute_quotation_count')

    status = fields.Selection([
        ('draft', 'Draft'), ('sent', 'Sent to Supplier'), ('quoted', 'Quotation Received'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    ai_recommended_supplier_id = fields.Many2one('res.partner', string='AI Recommended Supplier', readonly=True)
    ai_recommendation_note = fields.Text(string='AI Recommendation', readonly=True)
    ai_price_trend_note = fields.Text(string='AI Price Trend', readonly=True)
    ai_delay_risk_note = fields.Text(string='AI Delivery Delay Risk', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_quotation_count(self):
        for rec in self:
            rec.quotation_count = len(rec.quotation_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('rfq_number', _('New')) == _('New'):
                vals['rfq_number'] = self.env['ir.sequence'].next_by_code('garment.purchase.rfq') or _('New')
        return super().create(vals_list)

    def action_send(self):
        self.write({'status': 'sent'})

    def action_run_ai_recommendation(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            supplier, note = ai_engine.recommend_purchase_supplier(rec)
            rec.write({'ai_recommended_supplier_id': supplier.id if supplier else False,
                       'ai_recommendation_note': note})
        return True

    def action_run_ai_price_delay_prediction(self):
        """AI Purchase Price Prediction + AI Purchase Delay Prediction
        (SRS section 41)."""
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            _forecast, price_note = ai_engine.predict_price_trend(rec.material_name)
            _risk, delay_note = ai_engine.predict_delivery_risk(rec.supplier_id)
            rec.write({'ai_price_trend_note': price_note, 'ai_delay_risk_note': delay_note})
        return True

    def action_view_quotations(self):
        self.ensure_one()
        return {'name': _('Quotations'), 'type': 'ir.actions.act_window', 'res_model': 'garment.supplier.quotation',
                'view_mode': 'tree,form', 'domain': [('rfq_id', '=', self.id)],
                'context': {'default_rfq_id': self.id, 'default_supplier_id': self.supplier_id.id}}
