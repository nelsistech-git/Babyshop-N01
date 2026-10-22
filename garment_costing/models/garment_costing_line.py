# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentCostingLine(models.Model):
    """Operation Cost Calculation (SRS section 14) — garment.costing.line."""
    _name = 'garment.costing.line'
    _description = 'Garment Costing Operation Line'
    _order = 'sequence'

    cm_cost_id = fields.Many2one('garment.cm.cost', string='CM Cost Sheet', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    operation = fields.Selection([
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('washing', 'Washing'),
        ('finishing', 'Finishing'), ('packing', 'Packing'), ('embroidery', 'Embroidery'), ('printing', 'Printing'),
    ], string='Operation', required=True)
    description = fields.Char(string='Description')
    currency_id = fields.Many2one('res.currency', related='cm_cost_id.currency_id', store=True)
    line_cost = fields.Monetary(string='Cost', currency_field='currency_id')
