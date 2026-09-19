# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    fw_buyer_order_id = fields.Many2one('fw.buyer.order', string='Source Buyer Order',
                                         readonly=True, copy=False)
    fw_distribution_order_id = fields.Many2one('fw.distribution.order',
                                                string='Source Distribution Order',
                                                readonly=True, copy=False)
