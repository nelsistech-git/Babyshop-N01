# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentMerchNegotiation(models.Model):
    """Negotiation Management (SRS section 20) — garment.merch.negotiation.
    Full round-by-round commercial discussion history."""
    _name = 'garment.merch.negotiation'
    _description = 'Garment Merchandising Negotiation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'negotiation_date desc'

    negotiation_number = fields.Char(string='Negotiation Number', copy=False, readonly=True,
                                      default=lambda s: _('New'))
    quotation_id = fields.Many2one('garment.merch.quotation', string='Quotation', required=True, ondelete='cascade')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True)
    negotiation_date = fields.Date(string='Date', default=fields.Date.context_today)
    discussion_type = fields.Selection([
        ('email', 'Email'), ('call', 'Phone Call'), ('meeting', 'Meeting'), ('video_call', 'Video Call'),
    ], string='Discussion Type', default='email')
    currency_id = fields.Many2one('res.currency', related='quotation_id.currency_id', store=True)
    requested_price = fields.Monetary(string='Requested Price (Buyer Offer)', currency_field='currency_id')
    offered_price = fields.Monetary(string='Offered Price (Factory Target)', currency_field='currency_id')
    counter_offer = fields.Monetary(string='Counter Offer', currency_field='currency_id')
    quantity_revision = fields.Integer(string='Revised Quantity')
    delivery_revision = fields.Date(string='Revised Delivery Date')
    payment_revision = fields.Char(string='Revised Payment Terms')
    decision = fields.Selection([
        ('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('countered', 'Countered'),
    ], string='Decision', default='pending', tracking=True)
    notes = fields.Text(string='Notes')
    next_followup_date = fields.Date(string='Next Follow-up Date')
    handled_by_id = fields.Many2one('res.users', string='Handled By', default=lambda s: s.env.user)

    # Buyer Price Negotiation Management approval (Garment Merchandising Management
    # System SRS section 28: Buyer Offer / Factory Target Price / Final Price / Approval)
    final_price = fields.Monetary(string='Final Price', currency_field='currency_id', tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approval_date = fields.Date(string='Approval Date', readonly=True, copy=False)

    ai_suggested_counter_note = fields.Text(string='AI Counter-offer Suggestion', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('negotiation_number', _('New')) == _('New'):
                vals['negotiation_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.merch.negotiation') or _('New')
        return super().create(vals_list)

    def action_suggest_ai_counter(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            rec.ai_suggested_counter_note = ai_engine.suggest_negotiation_counter(rec)
        return True

    def action_approve(self):
        """Final approval of the negotiated price (SRS section 28: Approval)."""
        for rec in self:
            rec.write({
                'decision': 'accepted',
                'final_price': rec.final_price or rec.counter_offer or rec.offered_price,
                'approved_by_id': self.env.user.id,
                'approval_date': fields.Date.context_today(rec),
            })
