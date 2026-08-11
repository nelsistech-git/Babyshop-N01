from odoo import models, fields,_


class StockMoveInherit(models.Model):
    _inherit = 'stock.scrap'
    _description = "Scrap"

    order_by_id = fields.Many2one('res.users', string='Order By', ondelete='cascade')
    approve_by_id = fields.Many2one('res.users', string='Approve By', ondelete='cascade')