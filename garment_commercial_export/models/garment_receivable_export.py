# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Bangladesh Bank Reporting / Export Payment Realization (SRS sections
32-33) added onto garment_finance's garment.receivable, which already
tracks buyer/invoice/amount/received/outstanding/aging — this adds the
EXP Form and realizing-bank linkage central-bank reporting needs."""
from odoo import fields, models


class GarmentReceivableExport(models.Model):
    _inherit = 'garment.receivable'

    exp_form_id = fields.Many2one('garment.exp.form', string='EXP Form')
    realizing_bank_id = fields.Many2one('garment.bank.account', string='Realizing Bank')
    realization_date = fields.Date(string='Realization Date')
    bb_reporting_status = fields.Selection([
        ('pending', 'Pending'), ('reported', 'Reported to Bangladesh Bank'),
    ], string='BB Reporting Status', default='pending')
