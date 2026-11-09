# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api


class RealEstateHandoverWarrantyLink(models.Model):
    """Phase 9: adds a configurable warranty period to the Handover, so
    Warranty claims can compute whether they fall inside it without
    duplicating the handover date anywhere."""
    _inherit = 'real.estate.handover'

    warranty_period_months = fields.Integer(string='Warranty Period (Months)', default=12)
    warranty_expiry_date = fields.Date(string='Warranty Expiry Date',
                                        compute='_compute_warranty_expiry_date', store=True)
    warranty_ids = fields.One2many('real.estate.warranty', 'handover_id', string='Warranty Claims')
    warranty_count = fields.Integer(compute='_compute_warranty_count')

    @api.depends('handover_date', 'warranty_period_months', 'state')
    def _compute_warranty_expiry_date(self):
        for rec in self:
            if rec.handover_date and rec.state in ('handed_over', 'completed'):
                rec.warranty_expiry_date = rec.handover_date + relativedelta(
                    months=rec.warranty_period_months or 0)
            else:
                rec.warranty_expiry_date = False

    @api.depends('warranty_ids')
    def _compute_warranty_count(self):
        for rec in self:
            rec.warranty_count = len(rec.warranty_ids)
