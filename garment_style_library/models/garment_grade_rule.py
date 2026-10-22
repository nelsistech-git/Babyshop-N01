# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentGradeRule(models.Model):
    """Grade Rule Management (SRS section 18) — garment.grade.rule."""
    _name = 'garment.grade.rule'
    _description = 'Garment Grade Rule'
    _order = 'name'

    name = fields.Char(string='Rule Name', required=True)
    rule_code = fields.Char(string='Rule Code')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer')
    style_category_id = fields.Many2one('garment.style.category', string='Product Category')
    size_set_id = fields.Many2one('garment.size.set', string='Size Range')
    unit = fields.Selection([('cm', 'CM'), ('inch', 'Inch')], string='Unit', default='cm')
    line_ids = fields.One2many('garment.grade.rule.line', 'grade_rule_id', string='Grading Lines')
    active = fields.Boolean(default=True)

    def action_preview_grading(self):
        """Compute and DISPLAY a preview of graded measurements for all sizes,
        based on Base Size, Grade Rule and Size Sequence, before approval
        (SRS section 18: 'Provide preview before approval')."""
        self.ensure_one()
        return self.env['garment.grade.rule.preview.wizard'].create_from_grade_rule(self)


class GarmentGradeRuleLine(models.Model):
    _name = 'garment.grade.rule.line'
    _description = 'Garment Grade Rule Line'
    _order = 'sequence'

    grade_rule_id = fields.Many2one('garment.grade.rule', string='Grade Rule', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    measurement_point = fields.Char(string='Measurement Point', required=True)
    base_size_value = fields.Float(string='Base Size Value')
    increment_value = fields.Float(string='Increment Value')
    decrement_value = fields.Float(string='Decrement Value')
