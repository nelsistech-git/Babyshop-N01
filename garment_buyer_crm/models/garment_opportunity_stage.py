# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentOpportunityStage(models.Model):
    _name = 'garment.opportunity.stage'
    _description = 'Garment Opportunity Stage'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    is_won_stage = fields.Boolean(string='Is Order Confirmed Stage')
    is_lost_stage = fields.Boolean(string='Is Lost Stage')
    fold = fields.Boolean(string='Folded in Kanban')
