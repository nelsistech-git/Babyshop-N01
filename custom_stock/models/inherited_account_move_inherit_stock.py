from odoo import models, _, fields, api


class InheritedAccountMoveLineInheritStock(models.Model):
    _inherit = "account.move.line"
    _description = "Account Move Line Inherit"

    location_id = fields.Many2one('stock.location', string='Location',
                                  domain="[('state', '=', 'done')]")