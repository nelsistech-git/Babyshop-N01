from odoo import models, fields, api


class StockMoveLineInherit(models.Model):
    _inherit = 'stock.move.line'
    _description = "Stock Move Line Inherit"

    available_stock = fields.Float(string='On Hand Stock', related='move_id.available_stock', digits='Product Unit of Measure')
    remarks = fields.Char(string="Remarks")

    @api.onchange('remarks')
    def _onchange_remarks(self):
        for rec in self:
            rec.move_id.remarks = rec.remarks
