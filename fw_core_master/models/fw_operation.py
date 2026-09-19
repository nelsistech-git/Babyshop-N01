# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwOperation(models.Model):
    _name = 'fw.operation'
    _description = 'Footwear Operation Master (SMV Ready)'
    _order = 'process_type, sequence, name'

    name = fields.Char(string='Operation Name', required=True)
    code = fields.Char(string='Operation Code', required=True)
    process_type = fields.Selection([
        ('cutting', 'Cutting'),
        ('stitching', 'Stitching / Upper Closing'),
        ('assembly', 'Assembly / Lasting'),
        ('sole', 'Sole Making'),
        ('finishing', 'Finishing / Packing'),
        ('quality', 'Quality Check'),
    ], string='Process Type', required=True)
    sequence = fields.Integer(string='Default Sequence', default=10)
    machine_type = fields.Char(string='Machine / Equipment Type')
    standard_smv = fields.Float(string='Standard SMV (Minutes)',
                                 help="Standard Minute Value used for line balancing "
                                      "and costing in the Industrial Engineering module.")
    skill_level = fields.Selection([
        ('basic', 'Basic'),
        ('semi_skilled', 'Semi-Skilled'),
        ('skilled', 'Skilled'),
        ('expert', 'Expert'),
    ], string='Required Skill Level', default='semi_skilled')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Operation Code must be unique!'),
    ]

    def name_get(self):
        result = []
        for rec in self:
            label = "[%s] %s" % (rec.code, rec.name) if rec.code else rec.name
            result.append((rec.id, label))
        return result
