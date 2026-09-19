# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwShipment(models.Model):
    _inherit = 'fw.shipment'

    lc_id = fields.Many2one('fw.letter.of.credit', string='Letter of Credit',
                             domain="[('buyer_order_id', '=', order_id)]")
