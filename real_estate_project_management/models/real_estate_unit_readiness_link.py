# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateUnitReadinessLink(models.Model):
    """Phase 4: a Unit cannot be marked Ready while it still has open
    critical defects against it."""
    _inherit = 'real.estate.unit'

    qc_inspection_ids = fields.One2many('real.estate.qc.inspection', 'unit_id',
                                         string='QC Inspections')
    qc_inspection_count = fields.Integer(compute='_compute_unit_qc_counts')
    defect_ids = fields.One2many('real.estate.defect', 'unit_id', string='Defects')
    defect_count = fields.Integer(compute='_compute_unit_qc_counts')
    open_critical_defect_count = fields.Integer(compute='_compute_unit_qc_counts')

    @api.depends('defect_ids.status', 'defect_ids.severity', 'qc_inspection_ids')
    def _compute_unit_qc_counts(self):
        for rec in self:
            rec.qc_inspection_count = len(rec.qc_inspection_ids)
            rec.defect_count = len(rec.defect_ids)
            rec.open_critical_defect_count = len(rec.defect_ids.filtered(
                lambda d: d.severity == 'critical' and d.status != 'closed'))

    def action_set_ready(self):
        for rec in self:
            if rec.open_critical_defect_count:
                raise UserError(
                    'Unit "%s" cannot be marked Ready: %d critical defect(s) '
                    'are still open.' % (rec.name, rec.open_critical_defect_count))
        return super().action_set_ready()
