# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwBuyer(models.Model):
    _inherit = 'fw.buyer'

    compliance_ids = fields.One2many('fw.buyer.compliance', 'buyer_id',
                                      string='Compliance Certificates')
    compliance_count = fields.Integer(string='Certificates', compute='_compute_360_counts')
    audit_ids = fields.One2many('fw.buyer.audit', 'buyer_id', string='Audits')
    audit_count = fields.Integer(string='Audits', compute='_compute_360_counts')
    price_agreement_ids = fields.One2many('fw.buyer.price.agreement', 'buyer_id',
                                           string='Price Agreements')
    price_agreement_count = fields.Integer(string='Price Agreements',
                                            compute='_compute_360_counts')

    def _compute_360_counts(self):
        for rec in self:
            rec.compliance_count = len(rec.compliance_ids)
            rec.audit_count = len(rec.audit_ids)
            rec.price_agreement_count = len(rec.price_agreement_ids)

    def action_view_compliance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Compliance Certificates',
            'res_model': 'fw.buyer.compliance',
            'view_mode': 'tree,form',
            'domain': [('buyer_id', '=', self.id)],
            'context': {'default_buyer_id': self.id},
        }

    def action_view_audits(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Audits',
            'res_model': 'fw.buyer.audit',
            'view_mode': 'tree,form',
            'domain': [('buyer_id', '=', self.id)],
            'context': {'default_buyer_id': self.id},
        }

    def action_view_price_agreements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Price Agreements',
            'res_model': 'fw.buyer.price.agreement',
            'view_mode': 'tree,form',
            'domain': [('buyer_id', '=', self.id)],
            'context': {'default_buyer_id': self.id},
        }
