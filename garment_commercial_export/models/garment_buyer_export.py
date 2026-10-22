# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Adds the AI Buyer Commercial Risk button/note (SRS section 38) onto
garment_buyer_crm's garment.buyer, mirroring the ai_*_note pattern used
on garment.lc (garment_finance) and garment.shipment (garment_logistics)."""
from odoo import fields, models


class GarmentBuyerExport(models.Model):
    _inherit = 'garment.buyer'

    ai_commercial_risk_note = fields.Text(string='AI Commercial Risk', readonly=True)
    ai_commercial_risk_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    def action_run_ai_commercial_risk(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            note = ai_engine.predict_buyer_commercial_risk(rec)
            rec.write({'ai_commercial_risk_note': note, 'ai_commercial_risk_last_run': fields.Datetime.now()})
        return True
