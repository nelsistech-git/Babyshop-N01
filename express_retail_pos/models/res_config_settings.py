# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    express_pos_walkin_partner_id = fields.Many2one(
        'res.partner', string='Walk-in Customer',
        config_parameter='express_retail_pos.walkin_partner_id')
    express_pos_block_on_negative_stock = fields.Boolean(
        string='Block Sale on Insufficient Stock',
        config_parameter='express_retail_pos.block_on_negative_stock',
        help='If enabled, cashiers cannot add a product to the cart once stock on hand reaches zero.')
    express_pos_loyalty_point_rate = fields.Float(
        string='Currency Spent per Loyalty Point',
        config_parameter='express_retail_pos.loyalty_point_rate',
        default=100.0,
        help='E.g. 100 means the customer earns 1 point for every 100 currency units spent.')
    express_pos_gift_card_journal_id = fields.Many2one(
        'account.journal', string='Gift Card Journal',
        config_parameter='express_retail_pos.gift_card_journal_id',
        domain=[('type', 'in', ['cash', 'bank'])],
        help='Optional dedicated journal used to record the gift-card-redeemed portion of a checkout as a payment.')
    express_pos_default_receipt_format = fields.Selection(
        related='company_id.express_pos_default_receipt_format', readonly=False,
        string='Default Receipt Format',
        help='Billing/receipt layout used for any branch that does not set its own Receipt '
             'Format on the Showroom/Branch record.')
