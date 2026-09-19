# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwFactory(models.Model):
    _name = 'fw.factory'
    _description = 'Footwear Factory / Plant Master'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Factory Name', required=True, tracking=True)
    code = fields.Char(string='Factory Code', required=True, tracking=True)
    factory_type = fields.Selection([
        ('upper', 'Upper Factory'),
        ('sole', 'Sole Factory'),
        ('assembly', 'Assembly / Finishing'),
        ('leather', 'Leather Goods'),
        ('accessories', 'Accessories'),
        ('composite', 'Composite (Full Process)'),
    ], string='Factory Type', default='composite', tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Linked Warehouse')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    address = fields.Text(string='Address')
    line_ids = fields.One2many('fw.production.line', 'factory_id', string='Production Lines')
    line_count = fields.Integer(string='Line Count', compute='_compute_line_count')
    capacity_pairs_per_day = fields.Integer(string='Rated Capacity (Pairs/Day)')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Factory Code must be unique!'),
    ]

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def name_get(self):
        result = []
        for rec in self:
            label = "[%s] %s" % (rec.code, rec.name) if rec.code else rec.name
            result.append((rec.id, label))
        return result
