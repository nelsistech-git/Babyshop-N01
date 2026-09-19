# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwSampleLocation(models.Model):
    _name = 'fw.sample.location'
    _description = 'Footwear Sample Room Storage Location'
    _order = 'name'

    name = fields.Char(string='Location Name', required=True,
                        help="E.g. 'Rack A - Shelf 3', 'Swatch Cabinet 2 - Drawer 5'")
    location_code = fields.Char(string='Location Code')
    location_type = fields.Selection([
        ('rack', 'Rack'),
        ('bin', 'Bin'),
        ('drawer', 'Drawer'),
        ('cabinet', 'Cabinet'),
        ('other', 'Other'),
    ], string='Location Type', default='rack')
    capacity_note = fields.Char(string='Capacity Note')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Location Name must be unique!'),
    ]
