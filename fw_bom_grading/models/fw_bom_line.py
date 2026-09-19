# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError


class FwBomLine(models.Model):
    _inherit = 'fw.bom.line'

    grading_line_ids = fields.One2many('fw.bom.size.grading', 'bom_line_id',
                                        string='Size-Wise Consumption')
    has_size_grading = fields.Boolean(string='Size Grading Defined',
                                       compute='_compute_grading_summary', store=True)
    avg_graded_qty_per_pair = fields.Float(string='Avg. Graded Qty per Pair',
                                            compute='_compute_grading_summary', store=True,
                                            digits='Product Unit of Measure',
                                            help="Average of the size-wise quantities below. "
                                                 "Compare against 'Qty per Pair' above (the "
                                                 "flat fallback figure) as a sanity check.")

    @api.depends('grading_line_ids.qty_per_pair')
    def _compute_grading_summary(self):
        for rec in self:
            rec.has_size_grading = bool(rec.grading_line_ids)
            rec.avg_graded_qty_per_pair = (
                sum(rec.grading_line_ids.mapped('qty_per_pair')) / len(rec.grading_line_ids)
            ) if rec.grading_line_ids else 0.0

    def action_generate_size_grading(self):
        for rec in self:
            size_curve = rec.bom_id.style_id.size_curve_id
            if not size_curve:
                raise UserError(
                    "Style '%s' has no Size Curve set. Please set one on the Style master "
                    "first." % rec.bom_id.style_id.name)
            existing_sizes = rec.grading_line_ids.mapped('size_id')
            new_lines = [(0, 0, {
                'size_id': curve_line.size_id.id,
                'qty_per_pair': rec.qty_per_pair,
            }) for curve_line in size_curve.line_ids if curve_line.size_id not in existing_sizes]
            if new_lines:
                rec.grading_line_ids = new_lines
