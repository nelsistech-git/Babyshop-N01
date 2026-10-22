# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentMerchQuotation(models.Model):
    """Quotation Management (SRS section 19) — garment.merch.quotation."""
    _name = 'garment.merch.quotation'
    _description = 'Garment Merchandising Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'quotation_date desc'

    quotation_number = fields.Char(string='Quotation Number', copy=False, readonly=True, default=lambda s: _('New'))
    quotation_date = fields.Date(string='Quotation Date', default=fields.Date.context_today)
    inquiry_id = fields.Many2one('garment.merch.inquiry', string='Inquiry')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    rfq_id = fields.Many2one('garment.rfq', string='RFQ Reference')
    style_id = fields.Many2one('garment.style', string='Style')
    bom_id = fields.Many2one('garment.bom', string='Cost Sheet (BOM)', domain="[('style_id', '=', style_id)]")

    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    incoterm_id = fields.Many2one('account.incoterms', string='Incoterms')
    valid_until = fields.Date(string='Valid Until')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    delivery_terms = fields.Char(string='Delivery Terms')

    line_ids = fields.One2many('garment.merch.quotation.line', 'quotation_id', string='Quotation Lines')
    total_value = fields.Monetary(string='Total Value', compute='_compute_total', store=True,
                                   currency_field='currency_id')

    negotiation_ids = fields.One2many('garment.merch.negotiation', 'quotation_id', string='Negotiations')
    negotiation_count = fields.Integer(compute='_compute_negotiation_count')

    status = fields.Selection([
        ('draft', 'Draft'), ('internal_approval', 'Internal Approval'), ('sent', 'Sent'),
        ('buyer_review', 'Buyer Review'), ('negotiation', 'Negotiation'),
        ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('expired', 'Expired'),
    ], string='Status', default='draft', tracking=True)

    ai_suggested_price_note = fields.Text(string='AI Price Suggestion', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('line_ids.total_value')
    def _compute_total(self):
        for rec in self:
            rec.total_value = sum(rec.line_ids.mapped('total_value'))

    def _compute_negotiation_count(self):
        for rec in self:
            rec.negotiation_count = len(rec.negotiation_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('quotation_number', _('New')) == _('New'):
                vals['quotation_number'] = self.env['ir.sequence'].next_by_code('garment.merch.quotation') or _('New')
        return super().create(vals_list)

    def action_send(self):
        self.write({'status': 'sent'})
        if self.inquiry_id:
            self.inquiry_id.write({'status': 'quotation_sent'})

    def action_accept(self):
        self.write({'status': 'accepted'})
        if self.inquiry_id:
            self.inquiry_id.write({'status': 'order_confirmed'})

    def action_reject(self):
        self.write({'status': 'rejected'})

    def action_suggest_ai_price(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            note = ai_engine.suggest_quotation_price(rec)
            rec.ai_suggested_price_note = note
        return True

    def action_view_negotiations(self):
        self.ensure_one()
        return {'name': _('Negotiations'), 'type': 'ir.actions.act_window', 'res_model': 'garment.merch.negotiation',
                'view_mode': 'tree,form', 'domain': [('quotation_id', '=', self.id)],
                'context': {'default_quotation_id': self.id, 'default_buyer_id': self.buyer_id.id}}
