# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Grade Calculation preview (SRS section 18): 'Automatically calculate
measurements for all sizes based on Base Size, Grade Rule, Size Sequence.
Provide preview before approval.' garment.grade.rule.action_preview_grading()
opens this wizard instead of silently returning an unused python dict.
"""
from odoo import api, fields, models


class GarmentGradeRulePreviewWizard(models.TransientModel):
    _name = 'garment.grade.rule.preview.wizard'
    _description = 'Grade Rule Preview'

    grade_rule_id = fields.Many2one('garment.grade.rule', string='Grade Rule', required=True, readonly=True)
    size_set_id = fields.Many2one(related='grade_rule_id.size_set_id', string='Size Range', readonly=True)
    unit = fields.Selection(related='grade_rule_id.unit', string='Unit', readonly=True)
    line_ids = fields.One2many('garment.grade.rule.preview.line', 'wizard_id', string='Graded Preview', readonly=True)

    @api.model
    def create_from_grade_rule(self, grade_rule):
        """Compute the graded preview lines and return the wizard act_window."""
        lines = []
        for line in grade_rule.line_ids:
            for idx, size in enumerate(grade_rule.size_set_id.line_ids):
                increment = idx * (line.increment_value or 0.0)
                decrement = idx * (line.decrement_value or 0.0)
                value = (line.base_size_value or 0.0) + increment - decrement
                lines.append((0, 0, {
                    'measurement_point': line.measurement_point,
                    'size_code': size.size_code,
                    'is_base_size': size.is_base_size,
                    'computed_value': round(value, 2),
                }))
        wizard = self.create({'grade_rule_id': grade_rule.id, 'line_ids': lines})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Grade Rule Preview',
            'res_model': 'garment.grade.rule.preview.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }


class GarmentGradeRulePreviewLine(models.TransientModel):
    _name = 'garment.grade.rule.preview.line'
    _description = 'Grade Rule Preview Line'
    _order = 'measurement_point, id'

    wizard_id = fields.Many2one('garment.grade.rule.preview.wizard', ondelete='cascade')
    measurement_point = fields.Char(string='Measurement Point')
    size_code = fields.Char(string='Size')
    is_base_size = fields.Boolean(string='Base Size')
    computed_value = fields.Float(string='Computed Value')
