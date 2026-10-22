# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Export Incentive Management (SRS section 34) —
garment.export.incentive. Tracks Bangladesh Bank cash incentive claims
against an export shipment/invoice."""
from odoo import api, fields, models, _


class GarmentExportIncentive(models.Model):
    _name = 'garment.export.incentive'
    _description = 'Garment Export Incentive'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'application_date desc'

    claim_number = fields.Char(string='Claim Number', copy=False, readonly=True, default=lambda s: _('New'))
    export_documentation_id = fields.Many2one('garment.export.documentation', string='Export Reference',
                                               required=True, tracking=True)
    shipment_id = fields.Many2one('garment.shipment', string='Shipment', related='export_documentation_id.shipment_id',
                                   store=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', related='export_documentation_id.buyer_id',
                                store=True)

    incentive_type = fields.Selection([
        ('cash_incentive', 'Cash Incentive'), ('duty_drawback', 'Duty Drawback'),
        ('gsp_benefit', 'GSP Benefit'), ('other', 'Other Government Incentive'),
    ], string='Incentive Type', default='cash_incentive', required=True)
    incentive_rate = fields.Float(string='Incentive Rate (%)')

    export_value = fields.Monetary(string='Export Value', currency_field='currency_id')
    claim_amount = fields.Monetary(string='Claim Amount', compute='_compute_claim_amount', store=True,
                                    readonly=False, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    application_date = fields.Date(string='Application Date', default=fields.Date.context_today)
    bank_id = fields.Many2one('garment.bank.account', string='Bank')

    approval_status = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('under_review', 'Under Review'),
        ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True)

    received_amount = fields.Monetary(string='Received Amount', currency_field='currency_id')
    received_date = fields.Date(string='Received Date')
    outstanding_amount = fields.Monetary(string='Outstanding Amount', compute='_compute_outstanding', store=True,
                                          currency_field='currency_id')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('claim_number_uniq', 'unique(claim_number, company_id)', 'Claim Number must be unique per company!'),
    ]

    @api.depends('export_value', 'incentive_rate')
    def _compute_claim_amount(self):
        for rec in self:
            if rec.incentive_rate and rec.export_value:
                rec.claim_amount = rec.export_value * rec.incentive_rate / 100.0
            elif not rec.claim_amount:
                rec.claim_amount = 0.0

    @api.depends('claim_amount', 'received_amount')
    def _compute_outstanding(self):
        for rec in self:
            rec.outstanding_amount = rec.claim_amount - rec.received_amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('claim_number', _('New')) == _('New'):
                vals['claim_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.export.incentive') or _('New')
        return super().create(vals_list)
