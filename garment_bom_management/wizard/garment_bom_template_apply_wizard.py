# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Apply a BOM Template (SRS section 37.2) to a target garment.bom, seeding
its Fabric/Trim/Packaging BOM lines from the template's default materials."""

from odoo import fields, models, _
from odoo.exceptions import UserError


class GarmentBomTemplateApplyWizard(models.TransientModel):
    _name = 'garment.bom.template.apply.wizard'
    _description = 'Apply BOM Template'

    bom_id = fields.Many2one('garment.bom', string='Target BOM', required=True,
                              default=lambda s: s.env.context.get('active_id'))
    template_id = fields.Many2one('garment.bom.template', string='BOM Template', required=True)

    def action_apply(self):
        self.ensure_one()
        if not self.bom_id:
            raise UserError(_('No target BOM selected.'))
        Fabric = self.env['garment.fabric.bom']
        Trim = self.env['garment.trim.bom']
        Packaging = self.env['garment.packaging.bom']
        for line in self.template_id.line_ids:
            if line.material_category == 'fabric':
                Fabric.create({
                    'bom_id': self.bom_id.id, 'fabric_role': 'main', 'fabric_name': line.material_name,
                    'net_consumption': line.default_qty, 'uom': line.uom or 'kg',
                })
            elif line.material_category == 'trim':
                Trim.create({
                    'bom_id': self.bom_id.id, 'trim_type': 'accessory', 'description': line.material_name,
                    'consumption_per_piece': line.default_qty, 'uom': line.uom or 'pcs',
                })
            elif line.material_category == 'packaging':
                Packaging.create({
                    'bom_id': self.bom_id.id, 'packaging_type': 'poly_bag', 'description': line.material_name,
                    'consumption_per_piece': line.default_qty or 1.0, 'uom': line.uom or 'pcs',
                })
        return {'type': 'ir.actions.act_window_close'}
