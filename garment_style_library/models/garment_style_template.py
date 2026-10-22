# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models, _


class GarmentStyleTemplate(models.Model):
    """Reusable Style Templates (SRS section 26) — garment.style.template."""
    _name = 'garment.style.template'
    _description = 'Garment Style Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True,
                        help='e.g. Basic T-Shirt, Polo Shirt, Hoodie, Sweatshirt, Jogger Pant, Denim Pant...')
    style_category_id = fields.Many2one('garment.style.category', string='Product Category')
    size_set_id = fields.Many2one('garment.size.set', string='Default Measurement Chart / Size Set')
    grade_rule_id = fields.Many2one('garment.grade.rule', string='Default Grade Rule')
    default_bom_note = fields.Text(string='Default BOM (Notes)',
                                    help='Reference note until the BOM module is installed; once installed this '
                                         'can link to a garment.bom template record.')
    packaging_rule_note = fields.Text(string='Packaging Rules')
    label_note = fields.Text(string='Labels')
    default_tna_note = fields.Text(string='Default TNA Activities')
    active = fields.Boolean(default=True)

    def action_apply_to_new_style(self):
        """Create a new style pre-populated from this template (SRS section 28 automation)."""
        self.ensure_one()
        style = self.env['garment.style'].create({
            'style_name': _('New Style from %s') % self.name,
            'style_category_id': self.style_category_id.id,
        })
        if self.size_set_id:
            self.env['garment.measurement.chart'].create({
                'style_id': style.id,
                'product_type': self.style_category_id.name or '',
                'grade_rule_id': self.grade_rule_id.id,
            })
        return {
            'type': 'ir.actions.act_window', 'res_model': 'garment.style',
            'res_id': style.id, 'view_mode': 'form',
        }
