# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.merch.order.confirmation (garment_merchandising, an
existing dependency of this module) with the TNA Automation Engine (SRS
section 25): confirming an order automatically generates the TNA Master
and, when a matching buyer/category Template exists, its Template
Activities — with dates counted back from the order's Shipment Date.
"""
from odoo import fields, models, _


class GarmentMerchOrderConfirmationTnaExtension(models.Model):
    _inherit = 'garment.merch.order.confirmation'

    tna_ids = fields.One2many('garment.tna', 'order_confirmation_id', string='TNA')

    def action_confirm(self):
        res = super().action_confirm()
        self._auto_generate_tna()
        return res

    def _auto_generate_tna(self):
        """Automatic TNA Creation (SRS section 25): on confirmation, create
        the TNA Number and, if a Template matches this Buyer/Product
        Category, apply it (Automatic Date Calculation from the Shipment
        Date and Lead Time/Buyer Template)."""
        Tna = self.env['garment.tna']
        Template = self.env['garment.tna.template']
        for rec in self:
            if rec.tna_ids or not rec.shipment_date:
                continue
            style_category_id = rec.style_id.style_category_id.id if rec.style_id.style_category_id else False
            template = Template.search([
                ('active', '=', True),
                '|', ('buyer_id', '=', rec.buyer_id.id), ('buyer_id', '=', False),
                '|', ('style_category_id', '=', style_category_id), ('style_category_id', '=', False),
            ], order='buyer_id desc, style_category_id desc', limit=1)
            tna = Tna.create({
                'buyer_id': rec.buyer_id.id,
                'style_id': rec.style_id.id,
                'order_confirmation_id': rec.id,
                'order_number': rec.order_number,
                'purchase_order': rec.buyer_po_number,
                'shipment_date': rec.shipment_date,
                'factory': rec.factory,
                'production_unit': rec.production_unit,
                'merchandiser_id': rec.merchandiser_id.id,
                'template_id': template.id if template else False,
            })
            if template:
                tna.action_generate_from_template()
            rec.message_post(body=_('TNA %s auto-generated on order confirmation.') % (tna.tna_number or tna.name))
