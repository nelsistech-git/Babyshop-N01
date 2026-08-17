# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateUnitInstallmentLink(models.Model):
    """Phase 6: surfaces the Installment Plan on the Unit, per spec
    section 65's 'Unit form: ... Installments, Payments' smart buttons."""
    _inherit = 'real.estate.unit'

    installment_plan_ids = fields.One2many('real.estate.installment.plan', 'unit_id',
                                            string='Installment Plans')
    installment_plan_count = fields.Integer(compute='_compute_installment_stats')
    collection_ids = fields.One2many('real.estate.collection', 'unit_id', string='Collections')
    collection_count = fields.Integer(compute='_compute_installment_stats')

    @api.depends('installment_plan_ids', 'collection_ids')
    def _compute_installment_stats(self):
        for rec in self:
            rec.installment_plan_count = len(rec.installment_plan_ids)
            rec.collection_count = len(rec.collection_ids)
