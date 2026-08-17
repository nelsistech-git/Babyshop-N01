# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateProjectHandoverLink(models.Model):
    _inherit = 'real.estate.project'

    handover_ids = fields.One2many('real.estate.handover', 'project_id', string='Handovers')
    handover_count = fields.Integer(compute='_compute_handover_count')

    @api.depends('handover_ids')
    def _compute_handover_count(self):
        for rec in self:
            rec.handover_count = len(rec.handover_ids)

    def action_view_handovers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Handovers',
            'res_model': 'real.estate.handover',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
