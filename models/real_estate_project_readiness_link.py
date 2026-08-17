# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class RealEstateProjectReadinessLink(models.Model):
    """Phase 4: wires QC Inspections and Defects into the Project, and
    turns action_mark_ready() from a bare state transition (Phase 2) into
    a real readiness gate per spec section 32 - construction complete,
    mandatory QC passed, critical defects closed, utilities/documentation/
    safety completed, final inspection passed."""
    _inherit = 'real.estate.project'

    qc_inspection_ids = fields.One2many('real.estate.qc.inspection', 'project_id',
                                         string='QC Inspections')
    qc_inspection_count = fields.Integer(compute='_compute_qc_counts')
    defect_ids = fields.One2many('real.estate.defect', 'project_id', string='Defects')
    defect_count = fields.Integer(compute='_compute_qc_counts')
    open_critical_defect_count = fields.Integer(compute='_compute_qc_counts')

    readiness_utilities_completed = fields.Boolean(string='Utilities Completed')
    readiness_documentation_completed = fields.Boolean(string='Documentation Completed')
    readiness_safety_completed = fields.Boolean(string='Safety Completed')

    @api.depends('qc_inspection_ids', 'defect_ids.status', 'defect_ids.severity')
    def _compute_qc_counts(self):
        for rec in self:
            rec.qc_inspection_count = len(rec.qc_inspection_ids)
            rec.defect_count = len(rec.defect_ids)
            rec.open_critical_defect_count = len(rec.defect_ids.filtered(
                lambda d: d.severity == 'critical' and d.status != 'closed'))

    def action_mark_ready(self):
        for rec in self:
            failed_inspections = rec.qc_inspection_ids.filtered(lambda i: i.result == 'failed')
            if failed_inspections:
                raise UserError(
                    'Project "%s" cannot be marked Ready: %d QC inspection(s) '
                    'are still Failed. Resolve or re-inspect them first.' % (
                        rec.project_name, len(failed_inspections)))
            if rec.open_critical_defect_count:
                raise UserError(
                    'Project "%s" cannot be marked Ready: %d critical defect(s) '
                    'are still open.' % (rec.project_name, rec.open_critical_defect_count))
            if not (rec.readiness_utilities_completed and
                    rec.readiness_documentation_completed and
                    rec.readiness_safety_completed):
                raise UserError(
                    'Project "%s" cannot be marked Ready: Utilities, '
                    'Documentation and Safety completion checkboxes must '
                    'all be ticked first.' % rec.project_name)
        return super().action_mark_ready()

    def action_view_qc_inspections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'QC Inspections',
            'res_model': 'real.estate.qc.inspection',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_defects(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Defects',
            'res_model': 'real.estate.defect',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
