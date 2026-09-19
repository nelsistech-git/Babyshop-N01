# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwCrmStage(models.Model):
    _name = 'fw.crm.stage'
    _description = 'Footwear Buyer Acquisition Pipeline Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_won = fields.Boolean(string='Is Won Stage',
                             help="Marks this stage as representing a won deal. Moving a "
                                  "lead into this stage offers to convert it into a Buyer.")
    fold = fields.Boolean(string='Folded in Kanban')
