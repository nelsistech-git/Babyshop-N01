# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, models


class GarmentBuyer(models.Model):
    """Keep `res.partner.garment_buyer_id` in sync with `garment.buyer.partner_id`
    so record rules and controllers in this module can always resolve the
    buyer from the logged-in portal user's partner (see res_partner.py)."""
    _inherit = 'garment.buyer'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_portal_partner_link()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'partner_id' in vals:
            self._sync_portal_partner_link()
        return res

    def _sync_portal_partner_link(self):
        for rec in self:
            if rec.partner_id and rec.partner_id.garment_buyer_id != rec:
                rec.partner_id.garment_buyer_id = rec.id
