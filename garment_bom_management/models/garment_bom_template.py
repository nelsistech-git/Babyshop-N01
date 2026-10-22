# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""BOM Template Management (SRS section 37.2) — reusable default material
lists (e.g. Knit T-Shirt, Polo Shirt, Hoodie templates) that can be applied
to a garment.bom to seed its Fabric/Trim/Packaging lines in one click."""

from odoo import fields, models


class GarmentBomTemplate(models.Model):
    _name = 'garment.bom.template'
    _description = 'Garment BOM Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True)
    style_category_id = fields.Many2one('garment.style.category', string='Product Category')
    description = fields.Text(string='Description')
    consumption_rules = fields.Text(string='Consumption Rules')
    supplier_rules = fields.Text(string='Supplier Rules')
    packaging_rules = fields.Text(string='Packaging Rules')
    line_ids = fields.One2many('garment.bom.template.line', 'template_id', string='Default Materials')
    active = fields.Boolean(default=True)


class GarmentBomTemplateLine(models.Model):
    _name = 'garment.bom.template.line'
    _description = 'Garment BOM Template Line'
    _order = 'sequence'

    template_id = fields.Many2one('garment.bom.template', string='Template', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    material_category = fields.Selection([
        ('fabric', 'Fabric'), ('trim', 'Trim'), ('packaging', 'Packaging'),
    ], string='Material Category', required=True)
    material_name = fields.Char(string='Material Name', required=True)
    default_qty = fields.Float(string='Default Consumption Per Piece', default=1.0)
    uom = fields.Char(string='UoM')
    notes = fields.Char(string='Notes')
