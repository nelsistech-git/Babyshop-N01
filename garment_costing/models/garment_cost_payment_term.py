# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class GarmentCostPaymentTerm(models.Model):
    """Payment Terms Management (SRS section 28) — garment.cost.payment.term.
    Supports LC / TT / DP / DA / Advance Payment, tracked with payment
    percentage, due date and bank requirement — a costing can split payment
    across several rows (e.g. 30% TT advance + 70% LC at shipment)."""
    _name = 'garment.cost.payment.term'
    _description = 'Garment Costing Payment Term'
    _order = 'sequence'

    costing_id = fields.Many2one('garment.costing', string='Costing', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    payment_type = fields.Selection([
        ('lc', 'LC (Letter of Credit)'), ('tt', 'TT (Telegraphic Transfer)'),
        ('dp', 'DP (Documents against Payment)'), ('da', 'DA (Documents against Acceptance)'),
        ('advance', 'Advance Payment'),
    ], string='Payment Type', required=True)
    payment_percentage = fields.Float(string='Payment %')
    due_date = fields.Date(string='Due Date')
    bank_requirement = fields.Char(string='Bank Requirement')
    notes = fields.Text(string='Notes')

    @api.constrains('payment_percentage')
    def _check_payment_percentage(self):
        for rec in self:
            if rec.payment_percentage and not (0 < rec.payment_percentage <= 100):
                raise ValidationError(_('Payment %% must be between 0 and 100.'))
