# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentWashingRecipe(models.Model):
    """Washing Recipe master. See Production Management SRS s.43."""
    _name = 'garment.washing.recipe'
    _description = 'Garment Washing Recipe'
    _order = 'name'

    name = fields.Char(string='Recipe Name', required=True)
    wash_type = fields.Selection([
        ('normal', 'Normal Wash'), ('acid', 'Acid Wash'), ('enzyme', 'Enzyme Wash'),
        ('stone', 'Stone Wash'), ('bleach', 'Bleach Wash'), ('softener', 'Softener Wash'),
        ('special', 'Special Treatment'),
    ], string='Wash Type', required=True)
    temperature = fields.Float(string='Temperature (°C)')
    duration_minutes = fields.Float(string='Duration (Minutes)')
    machine_setting = fields.Char(string='Machine Setting')
    chemical_line_ids = fields.One2many('garment.washing.chemical.line', 'recipe_id', string='Chemical List')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)


class GarmentWashingChemicalLine(models.Model):
    """Chemical Consumption line — used by both the recipe (planned
    chemical list) and the washing order (actual consumption). See
    Production Management SRS s.44."""
    _name = 'garment.washing.chemical.line'
    _description = 'Garment Washing Chemical Line'
    _order = 'id'

    recipe_id = fields.Many2one('garment.washing.recipe', string='Recipe', ondelete='cascade')
    washing_order_id = fields.Many2one('garment.washing.order', string='Washing Order', ondelete='cascade')
    chemical_name = fields.Char(string='Chemical', required=True)
    material_id = fields.Many2one('garment.material', string='Material Reference')
    batch = fields.Char(string='Batch')
    uom = fields.Char(string='UoM', default='KG')
    required_qty = fields.Float(string='Required Quantity')
    used_qty = fields.Float(string='Used Quantity')
    variance_qty = fields.Float(string='Variance', compute='_compute_variance', store=True)
    cost = fields.Monetary(string='Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    operator_id = fields.Many2one('garment.hr.employee', string='Operator')

    def _compute_variance(self):
        for rec in self:
            rec.variance_qty = (rec.used_qty or 0.0) - (rec.required_qty or 0.0)
