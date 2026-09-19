# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwShipment(models.Model):
    _inherit = 'fw.shipment'

    consolidation_id = fields.Many2one('fw.container.consolidation',
                                        string='Container Consolidation')
