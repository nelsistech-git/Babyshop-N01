# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import models


class GarmentQualityInspection(models.Model):
    """Adds `portal.mixin` to garment.quality.inspection (garment_quality) -
    SRS section 29 (Buyer Quality Portal)."""
    _name = 'garment.quality.inspection'
    _inherit = ['garment.quality.inspection', 'portal.mixin']

    def _compute_access_url(self):
        super()._compute_access_url()
        for inspection in self:
            inspection.access_url = '/my/quality/%d' % inspection.id
