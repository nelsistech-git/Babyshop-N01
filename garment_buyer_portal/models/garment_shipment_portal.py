# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import models


class GarmentShipment(models.Model):
    """Adds `portal.mixin` to garment.shipment (garment_logistics) -
    SRS section 30 (Buyer Shipment Tracking)."""
    _name = 'garment.shipment'
    _inherit = ['garment.shipment', 'portal.mixin']

    def _compute_access_url(self):
        super()._compute_access_url()
        for shipment in self:
            shipment.access_url = '/my/shipments/%d' % shipment.id
