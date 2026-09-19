# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwIncentiveScheme(models.Model):
    _name = 'fw.incentive.scheme'
    _description = 'Footwear Worker Incentive Scheme'
    _order = 'name'

    name = fields.Char(string='Scheme Name', required=True)
    scheme_type = fields.Selection([
        ('piece_rate', 'Piece Rate'),
        ('efficiency_bonus', 'Efficiency Bonus'),
    ], string='Scheme Type', required=True, default='piece_rate')

    operation_id = fields.Many2one('fw.operation', string='Operation',
                                    help="For Piece Rate schemes, optionally restrict this "
                                         "scheme to a specific operation.")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    rate_per_piece = fields.Monetary(string='Rate per Piece', currency_field='currency_id',
                                      help="Used when Scheme Type = Piece Rate.")

    efficiency_threshold_percent = fields.Float(string='Efficiency Threshold (%)', default=100.0,
                                                 help="Minimum efficiency % required before any "
                                                      "bonus applies. Used when Scheme Type = "
                                                      "Efficiency Bonus.")
    bonus_rate_per_percent = fields.Monetary(string='Bonus per % Above Threshold',
                                              currency_field='currency_id',
                                              help="Bonus amount for each whole percentage "
                                                   "point of efficiency above the threshold. "
                                                   "Used when Scheme Type = Efficiency Bonus.")

    active = fields.Boolean(default=True)
