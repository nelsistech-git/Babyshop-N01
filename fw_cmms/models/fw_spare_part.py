# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwSparePart(models.Model):
    _name = 'fw.spare.part'
    _description = 'Footwear Machine Spare Part Master'
    _order = 'name'

    name = fields.Char(string='Spare Part Name', required=True)
    code = fields.Char(string='Part Code', required=True)
    category = fields.Selection([
        ('mechanical', 'Mechanical'),
        ('electrical', 'Electrical'),
        ('electronic', 'Electronic'),
        ('consumable', 'Consumable'),
        ('other', 'Other'),
    ], string='Category', default='other')

    uom_id = fields.Many2one('uom.uom', string='UoM',
                              default=lambda self: self.env.ref('uom.product_uom_unit', False))
    current_stock = fields.Float(string='Current Stock', default=0.0)
    min_stock_level = fields.Float(string='Reorder Level', default=0.0)
    below_reorder = fields.Boolean(string='Below Reorder Level', compute='_compute_below_reorder',
                                    store=True)

    unit_cost = fields.Float(string='Unit Cost')
    vendor_id = fields.Many2one('res.partner', string='Preferred Vendor')

    active = fields.Boolean(default=True)

    @api.constrains('min_stock_level', 'unit_cost')
    def _check_non_negative(self):
        for rec in self:
            if rec.min_stock_level < 0:
                raise ValidationError("Reorder Level cannot be negative.")
            if rec.unit_cost < 0:
                raise ValidationError("Unit Cost cannot be negative.")

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Spare Part Code must be unique!'),
    ]

    @api.depends('current_stock', 'min_stock_level')
    def _compute_below_reorder(self):
        for rec in self:
            rec.below_reorder = rec.current_stock < rec.min_stock_level

    def name_get(self):
        result = []
        for rec in self:
            label = "[%s] %s" % (rec.code, rec.name) if rec.code else rec.name
            result.append((rec.id, label))
        return result
