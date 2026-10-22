# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import models


class GarmentTechpack(models.Model):
    """Adds `portal.mixin` to garment.techpack (garment_techpack) so buyer
    sign-off items can deep-link back to the source Tech Pack -
    SRS sections 12, 32 (Buyer Document Approval)."""
    _name = 'garment.techpack'
    _inherit = ['garment.techpack', 'portal.mixin']

    def _compute_access_url(self):
        super()._compute_access_url()
        for techpack in self:
            techpack.access_url = '/my/techpacks/%d' % techpack.id
