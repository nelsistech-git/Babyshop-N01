# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwDefectCode(models.Model):
    _name = 'fw.defect.code'
    _description = 'Footwear Defect Code Master'
    _order = 'category, code'

    name = fields.Char(string='Defect Name', required=True)
    code = fields.Char(string='Defect Code', required=True)
    category = fields.Selection([
        ('upper', 'Upper'),
        ('sole', 'Sole'),
        ('stitching', 'Stitching'),
        ('assembly', 'Assembly / Lasting'),
        ('finishing', 'Finishing'),
        ('packing', 'Packing'),
        ('material', 'Material / Fabric'),
        ('other', 'Other'),
    ], string='Category', required=True, default='other')
    severity = fields.Selection([
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ], string='Severity', required=True, default='minor')
    description = fields.Char(string='Description')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Defect Code must be unique!'),
    ]

    def name_get(self):
        result = []
        for rec in self:
            label = "[%s] %s" % (rec.code, rec.name) if rec.code else rec.name
            result.append((rec.id, label))
        return result
