# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    fw_style_id = fields.Many2one('fw.style', string='Footwear Style')
    fw_buyer_order_id = fields.Many2one('fw.buyer.order', string='Buyer Order')
    fw_factory_id = fields.Many2one('fw.factory', string='Factory')
    fw_production_line_id = fields.Many2one(
        'fw.production.line', string='Production Line',
        domain="[('factory_id', '=', fw_factory_id)]")
    fw_production_order_id = fields.Many2one(
        'fw.production.order', string='Footwear Production Order', readonly=True, copy=False,
        help="The footwear stage-tracking order that generated this Manufacturing Order, "
             "if any.")
