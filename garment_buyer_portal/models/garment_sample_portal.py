# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import models


class GarmentSample(models.Model):
    """Adds `portal.mixin` to garment.sample (garment_sample_management) so
    it gets a portal access URL/token like garment.order already has -
    SRS section 12 (Buyer Sample Approval Portal)."""
    _name = 'garment.sample'
    _inherit = ['garment.sample', 'portal.mixin']

    def _compute_access_url(self):
        super()._compute_access_url()
        for sample in self:
            sample.access_url = '/my/samples/%d' % sample.id
