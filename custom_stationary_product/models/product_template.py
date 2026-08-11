# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_stationary_product = fields.Boolean(
        string='Stationary Product',
        default=False,
        help='Check this box to mark the product as a Stationary Product. '
             'Stationary products will appear under HR > Employees > Stationary Product '
             'and will be hidden from Inventory > Products.',
    )
