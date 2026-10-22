# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""LC Amendment Management (SRS section 14) — garment.lc.amendment.
garment_finance's garment.lc only keeps a bare amendment_count integer;
this model gives it the structured old-value/new-value/reason/approval
record the SRS asks for, and bumps that counter when one is created."""
from odoo import api, fields, models


class GarmentLcAmendment(models.Model):
    _name = 'garment.lc.amendment'
    _description = 'Garment LC Amendment'
    _order = 'lc_id, amendment_number'

    lc_id = fields.Many2one('garment.lc', string='LC', required=True, ondelete='cascade')
    amendment_number = fields.Char(string='Amendment Number', required=True)
    amendment_date = fields.Date(string='Amendment Date', default=fields.Date.context_today)
    change_summary = fields.Char(string='Change Summary', required=True)
    old_value = fields.Char(string='Old Value')
    new_value = fields.Char(string='New Value')
    reason = fields.Text(string='Reason')
    approval_date = fields.Date(string='Approval Date')
    status = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted to Bank'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.lc_id.amendment_count = len(rec.lc_id.amendment_ids)
        return records

    def unlink(self):
        lcs = self.mapped('lc_id')
        res = super().unlink()
        for lc in lcs:
            lc.amendment_count = len(lc.amendment_ids)
        return res
