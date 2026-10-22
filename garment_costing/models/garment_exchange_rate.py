# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentExchangeRate(models.Model):
    """Currency & Exchange Rate Management (SRS section 24) —
    garment.exchange.rate."""
    _name = 'garment.exchange.rate'
    _description = 'Garment Exchange Rate'
    _order = 'effective_date desc'

    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    target_currency_id = fields.Many2one('res.currency', string='Target Currency', required=True,
                                          default=lambda s: s.env.company.currency_id)
    rate = fields.Float(string='Exchange Rate', required=True, digits=(12, 6))
    effective_date = fields.Date(string='Effective Date', default=fields.Date.context_today, required=True)
    source = fields.Char(string='Source', help='e.g. Bangladesh Bank, XE.com, Bank Rate')
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    active = fields.Boolean(default=True)

    @api.model
    def get_rate(self, currency_id, target_currency_id, date=None):
        """Return the most recent applicable rate for currency_id ->
        target_currency_id on or before `date` (SRS section 24: "Automatic
        calculation: USD Cost x Exchange Rate = BDT Cost"). Returns 0.0 when
        no rate is on file yet."""
        if not currency_id or not target_currency_id:
            return 0.0
        date = date or fields.Date.context_today(self)
        rate = self.search([
            ('currency_id', '=', currency_id.id),
            ('target_currency_id', '=', target_currency_id.id),
            ('effective_date', '<=', date),
        ], order='effective_date desc', limit=1)
        return rate.rate if rate else 0.0
