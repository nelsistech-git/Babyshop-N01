from odoo import models, fields


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_stationary_location = fields.Boolean(
        string='Is Stationary Location',
        default=False,
        help='Check this if this location is used for stationary stock.',
    )
