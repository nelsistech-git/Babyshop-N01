# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwBomLine(models.Model):
    _inherit = 'fw.bom.line'

    sub_bom_id = fields.Many2one('fw.bom.version', string='Sub-Assembly BOM',
                                  help="If this component is itself a pre-assembled unit "
                                       "with its own Bill of Materials, link that BOM Version "
                                       "here. Use 'Sync Cost from Sub-Assembly' to pull its "
                                       "current Total Cost into this line's Unit Cost.")
    is_sub_assembly = fields.Boolean(string='Is Sub-Assembly', compute='_compute_is_sub_assembly',
                                      store=True)

    @api.depends('sub_bom_id')
    def _compute_is_sub_assembly(self):
        for rec in self:
            rec.is_sub_assembly = bool(rec.sub_bom_id)

    @api.constrains('sub_bom_id')
    def _check_no_circular_subassembly(self):
        for rec in self:
            if not rec.sub_bom_id or not rec.bom_id:
                continue
            visited = set()
            to_visit = [rec.sub_bom_id.id]
            while to_visit:
                current_id = to_visit.pop()
                if current_id in visited:
                    continue
                visited.add(current_id)
                if current_id == rec.bom_id.id:
                    raise ValidationError(
                        "Circular reference detected: BOM '%s' cannot use itself (directly "
                        "or through a chain of sub-assemblies) as a sub-assembly component."
                        % rec.bom_id.name)
                current_bom = self.env['fw.bom.version'].browse(current_id)
                for line in current_bom.line_ids:
                    if line.sub_bom_id:
                        to_visit.append(line.sub_bom_id.id)

    @api.onchange('sub_bom_id')
    def _onchange_sub_bom_id(self):
        if self.sub_bom_id:
            self.unit_cost = self.sub_bom_id.total_cost

    def action_sync_cost_from_subbom(self):
        for rec in self:
            if rec.sub_bom_id:
                rec.unit_cost = rec.sub_bom_id.total_cost
