# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Extends garment_finance's garment.lc with LC Types / Back-to-Back LC
Management (SRS sections 11-13, 16-17), structured Amendments (section
14) and LC Utilization Tracking (section 18). garment_finance's model
already carries the generic buyer/bank/amount/expiry/workflow — this adds
the Master-vs-BTB distinction and the utilized/balance computation."""
from odoo import api, fields, models


class GarmentLcExport(models.Model):
    _inherit = 'garment.lc'

    lc_type = fields.Selection([
        ('master', 'Master LC'), ('export', 'Export LC'), ('back_to_back', 'Back-to-Back LC'),
        ('sight', 'Sight LC'), ('usance', 'Usance LC'),
    ], string='LC Type', default='export', tracking=True)

    master_lc_id = fields.Many2one('garment.lc', string='Master LC Reference',
                                    domain="[('lc_type', 'in', ('master', 'export'))]",
                                    help='For a Back-to-Back LC: the Master export LC it is opened against.')
    btb_lc_ids = fields.One2many('garment.lc', 'master_lc_id', string='Back-to-Back LCs')

    supplier_id = fields.Many2one('garment.supplier', string='Supplier',
                                   help='Fabric/accessory supplier this Back-to-Back LC is opened for.')

    issuing_bank_id = fields.Many2one('garment.bank.account', string='Issuing Bank')
    advising_bank_id = fields.Many2one('garment.bank.account', string='Advising Bank')
    buyer_bank_id = fields.Many2one('garment.bank.account', string="Buyer's Bank")

    amendment_ids = fields.One2many('garment.lc.amendment', 'lc_id', string='Amendments')

    export_documentation_ids = fields.One2many('garment.export.documentation', 'lc_id',
                                                 string='Export Documents Drawn Under This LC')
    import_permission_ids = fields.One2many('garment.import.permission', 'btb_lc_id',
                                             string='Import Permissions Opened Under This LC')

    utilized_amount = fields.Monetary(string='Utilized Amount', compute='_compute_utilization', store=True,
                                       currency_field='currency_id')
    balance_amount = fields.Monetary(string='Balance Amount', compute='_compute_utilization', store=True,
                                      currency_field='currency_id')
    utilization_pct = fields.Float(string='Utilization %', compute='_compute_utilization', store=True)

    @api.depends('lc_amount', 'lc_type', 'export_documentation_ids.total_value', 'import_permission_ids.value')
    def _compute_utilization(self):
        for rec in self:
            if rec.lc_type == 'back_to_back':
                utilized = sum(rec.import_permission_ids.mapped('value'))
            else:
                utilized = sum(rec.export_documentation_ids.mapped('total_value'))
            rec.utilized_amount = utilized
            rec.balance_amount = rec.lc_amount - utilized
            rec.utilization_pct = (utilized / rec.lc_amount * 100.0) if rec.lc_amount else 0.0
