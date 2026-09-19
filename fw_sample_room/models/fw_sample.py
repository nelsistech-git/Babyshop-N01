# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwSample(models.Model):
    _inherit = 'fw.sample'

    storage_location_id = fields.Many2one('fw.sample.location', string='Storage Location',
                                           help="Where the physical sample is stored in the "
                                                "sample room.")
