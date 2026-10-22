# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models, _


class GarmentAIBulkScoringWizard(models.TransientModel):
    _name = 'garment.ai.bulk.scoring.wizard'
    _description = 'Run AI Lead Scoring on Multiple Buyers'

    buyer_ids = fields.Many2many('garment.buyer', string='Buyers')
    only_active_leads = fields.Boolean(string='Only Active Leads (exclude Inactive/Blacklisted)', default=True)

    def action_run(self):
        self.ensure_one()
        buyers = self.buyer_ids
        if self.only_active_leads:
            buyers = buyers.filtered(lambda b: b.buyer_status not in ('inactive', 'blacklisted'))
        buyers.action_run_ai_analysis()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Buyers'),
            'res_model': 'garment.buyer',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', buyers.ids)],
        }
