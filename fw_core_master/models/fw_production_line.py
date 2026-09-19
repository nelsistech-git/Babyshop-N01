# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwProductionLine(models.Model):
    _name = 'fw.production.line'
    _description = 'Footwear Production Line Master'
    _order = 'factory_id, name'

    name = fields.Char(string='Line Name', required=True)
    code = fields.Char(string='Line Code', required=True)
    factory_id = fields.Many2one('fw.factory', string='Factory', required=True,
                                  ondelete='cascade')
    line_type = fields.Selection([
        ('cutting', 'Cutting'),
        ('stitching', 'Stitching / Upper'),
        ('assembly', 'Assembly / Lasting'),
        ('finishing', 'Finishing / Packing'),
        ('mixed', 'Mixed Process'),
    ], string='Line Type', default='mixed')
    workstation_count = fields.Integer(string='Number of Workstations')
    rated_capacity_pairs_per_day = fields.Integer(string='Rated Capacity (Pairs/Day)')
    supervisor_id = fields.Many2one('hr.employee', string='Line Supervisor')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_factory_uniq', 'unique(code, factory_id)',
         'Line Code must be unique per factory!'),
    ]

    def name_get(self):
        result = []
        for rec in self:
            label = "%s / %s" % (rec.factory_id.name, rec.name) if rec.factory_id else rec.name
            result.append((rec.id, label))
        return result
