# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models, _


class GarmentCostNegotiation(models.Model):
    """Buyer Price Negotiation (SRS section 19) — garment.cost.negotiation.
    Tracks buyer negotiation history: one row per negotiation round, with
    submitted price, buyer target price, negotiated price, final price,
    notes and approval."""
    _name = 'garment.cost.negotiation'
    _description = 'Garment Costing Buyer Negotiation'
    _order = 'negotiation_date desc, sequence'

    costing_id = fields.Many2one('garment.costing', string='Costing', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    negotiation_date = fields.Date(string='Negotiation Date', default=fields.Date.context_today)
    submitted_price = fields.Monetary(string='Submitted Price', currency_field='currency_id')
    buyer_target_price = fields.Monetary(string='Buyer Target Price', currency_field='currency_id')
    negotiated_price = fields.Monetary(string='Negotiated Price', currency_field='currency_id')
    final_price = fields.Monetary(string='Final Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='costing_id.currency_id', store=True)
    negotiation_notes = fields.Text(string='Negotiation Notes')
    approval_status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval', default='pending')
    approved_by_id = fields.Many2one('res.users', string='Approved By')

    def action_approve(self):
        for rec in self:
            rec.write({'approval_status': 'approved', 'approved_by_id': self.env.user.id})
            if rec.final_price:
                rec.costing_id.message_post(
                    body=_('Buyer negotiation round approved: Final Price %.2f') % rec.final_price)

    def action_reject(self):
        self.write({'approval_status': 'rejected', 'approved_by_id': self.env.user.id})
