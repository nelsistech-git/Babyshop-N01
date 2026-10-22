# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentReceivable(models.Model):
    """Customer Receivable Management (SRS section 15) —
    garment.receivable."""
    _name = 'garment.receivable'
    _description = 'Garment Buyer Receivable'
    _inherit = ['mail.thread']
    _order = 'due_date'

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True)
    export_invoice_reference = fields.Char(string='Export Invoice Reference', required=True)
    shipment_id = fields.Many2one('garment.shipment', string='Shipment')
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    invoice_date = fields.Date(string='Invoice Date')
    due_date = fields.Date(string='Due Date')
    received_amount = fields.Monetary(string='Received Amount', currency_field='currency_id')
    outstanding_amount = fields.Monetary(string='Outstanding Amount', compute='_compute_outstanding', store=True,
                                          currency_field='currency_id')
    aging_days = fields.Integer(string='Aging (days)', compute='_compute_outstanding', store=True)
    aging_bucket = fields.Selection([
        ('current', 'Current'), ('30', '1-30 Days'), ('60', '31-60 Days'),
        ('90', '61-90 Days'), ('90_plus', '90+ Days'),
    ], string='Aging Bucket', compute='_compute_outstanding', store=True)
    status = fields.Selection([
        ('outstanding', 'Outstanding'), ('partially_received', 'Partially Received'), ('received', 'Received'),
    ], string='Status', compute='_compute_outstanding', store=True, tracking=True)

    @api.depends('amount', 'received_amount', 'due_date')
    def _compute_outstanding(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.outstanding_amount = max(0.0, (rec.amount or 0.0) - (rec.received_amount or 0.0))
            rec.status = ('received' if rec.outstanding_amount <= 0
                          else 'partially_received' if rec.received_amount else 'outstanding')
            if rec.due_date and rec.outstanding_amount > 0:
                days = (today - rec.due_date).days
                rec.aging_days = max(0, days)
                if days <= 0:
                    rec.aging_bucket = 'current'
                elif days <= 30:
                    rec.aging_bucket = '30'
                elif days <= 60:
                    rec.aging_bucket = '60'
                elif days <= 90:
                    rec.aging_bucket = '90'
                else:
                    rec.aging_bucket = '90_plus'
            else:
                rec.aging_days = 0
                rec.aging_bucket = 'current'
