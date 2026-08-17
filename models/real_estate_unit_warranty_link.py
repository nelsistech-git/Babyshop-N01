# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateUnitWarrantyLink(models.Model):
    _inherit = 'real.estate.unit'

    warranty_ids = fields.One2many('real.estate.warranty', 'unit_id', string='Warranty Claims')
    warranty_count = fields.Integer(compute='_compute_warranty_count')

    @api.depends('warranty_ids.status')
    def _compute_warranty_count(self):
        for rec in self:
            rec.warranty_count = len(rec.warranty_ids)
