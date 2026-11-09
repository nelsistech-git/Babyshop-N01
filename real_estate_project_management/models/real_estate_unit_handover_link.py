# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateUnitHandoverLink(models.Model):
    _inherit = 'real.estate.unit'

    handover_ids = fields.One2many('real.estate.handover', 'unit_id', string='Handovers')
    handover_count = fields.Integer(compute='_compute_handover_count')

    @api.depends('handover_ids')
    def _compute_handover_count(self):
        for rec in self:
            rec.handover_count = len(rec.handover_ids)
