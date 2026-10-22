# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""BOM Comparison Tool (SRS section 26 Version Comparison / section 38) —
compares two garment.bom records (typically two versions/revisions of the
same style) across Material, Consumption, Cost and Supplier."""

from odoo import fields, models, _
from odoo.exceptions import UserError


class GarmentBomCompareWizard(models.TransientModel):
    _name = 'garment.bom.compare.wizard'
    _description = 'Compare BOM Versions'

    bom_id_1 = fields.Many2one('garment.bom', string='BOM (A)', required=True)
    bom_id_2 = fields.Many2one('garment.bom', string='BOM (B)', required=True)
    comparison_result = fields.Html(string='Comparison Result', readonly=True)

    def action_compare(self):
        self.ensure_one()
        if self.bom_id_1 == self.bom_id_2:
            raise UserError(_('Choose two different BOMs to compare.'))
        a, b = self.bom_id_1, self.bom_id_2
        parts = ['<h4>Material Comparison</h4>']

        def line_key(line, name_field):
            return getattr(line, name_field, False) or line.display_name

        for label, field, name_field in (
            ('Fabric', 'fabric_bom_ids', 'fabric_name'),
            ('Trim', 'trim_bom_ids', 'description'),
            ('Packaging', 'packaging_bom_ids', 'description'),
        ):
            names_a = {line_key(l, name_field) for l in getattr(a, field)}
            names_b = {line_key(l, name_field) for l in getattr(b, field)}
            added = names_b - names_a
            removed = names_a - names_b
            parts.append('<b>%s</b>: Added: %s | Removed: %s<br/>' % (
                label, ', '.join(added) or '-', ', '.join(removed) or '-'))

        parts.append('<h4>Consumption Comparison</h4>')
        old_net = sum(a.fabric_bom_ids.mapped('net_consumption'))
        new_net = sum(b.fabric_bom_ids.mapped('net_consumption'))
        diff_pct = ((new_net - old_net) / old_net * 100.0) if old_net else 0.0
        parts.append('Old Consumption: %.3f | New Consumption: %.3f | Difference: %.1f%%<br/>' % (
            old_net, new_net, diff_pct))

        parts.append('<h4>Cost Comparison</h4>')
        parts.append('Previous Cost/Piece: %.2f | Current Cost/Piece: %.2f | Cost Variance: %.2f<br/>' % (
            a.cost_per_piece, b.cost_per_piece, b.cost_per_piece - a.cost_per_piece))

        parts.append('<h4>Supplier Comparison</h4>')
        sup_a = {s.material_reference: s.supplier_id.name for s in a.supplier_ids}
        sup_b = {s.material_reference: s.supplier_id.name for s in b.supplier_ids}
        for ref, sup_b_name in sup_b.items():
            sup_a_name = sup_a.get(ref)
            if sup_a_name and sup_a_name != sup_b_name:
                parts.append('%s: %s → %s<br/>' % (ref, sup_a_name, sup_b_name))

        self.comparison_result = ''.join(parts)
        return {
            'name': _('Compare BOM Versions'),
            'type': 'ir.actions.act_window',
            'res_model': 'garment.bom.compare.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
