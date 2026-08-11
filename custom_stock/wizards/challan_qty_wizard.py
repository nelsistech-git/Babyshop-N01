from odoo import models, fields, _, api
from odoo.exceptions import AccessError


class ChallanQtyWizard(models.TransientModel):
    _name = 'challan.qty.wizard'
    _description = 'Challan Quantity Wizard'

    stock_move_ids = fields.One2many('challan.qty.line.wizard', 'head_id', string='Stock Move Line')

    @api.model
    def default_get(self, fields):
        res = super(ChallanQtyWizard, self).default_get(fields)
        rec_list = []
        stock_picking_id = self.env.context.get('active_id')
        pr_err_msg = self.env.context.get('pr_err_msg')
        stock_picking_obj = self.env['stock.picking'].browse(stock_picking_id)
        if stock_picking_obj:
            for line in stock_picking_obj.move_ids_without_package:
                product_id = line.product_id
                product_uom_qty = line.product_uom_qty
                challan_qty = line.challan_qty
                rec_list.append(
                    (0, 0, {'stock_move_id': line.id, 'product_id': product_id.id, 'product_uom_qty': product_uom_qty, 'challan_qty': challan_qty}))
            if 'stock_move_ids' in fields:
                res.update({'stock_move_ids': rec_list})
        return res

    def action_update(self):
        stock_picking_id = self.env.context.get('active_id')
        for line in self.stock_move_ids:
            stock_move_id = line.stock_move_id.id
            # if line.challan_qty > line.product_uom_qty:
            #     raise AccessError(
            #         _("Challan quantity cannot be more than demand quantity.")
            #     )
            if line.challan_qty < 0:
                raise AccessError(
                    _("Challan quantity cannot be zero.")
                )
            query = """ UPDATE stock_move SET challan_qty = %s WHERE id = %s and picking_id = %s """
            self.env.cr.execute(query, [line.challan_qty, stock_move_id, stock_picking_id])


class ChallanQtyLineWizard(models.TransientModel):
    _name = 'challan.qty.line.wizard'
    _description = 'Challan Quantity Line Wizard'

    head_id = fields.Many2one('challan.qty.wizard', required=True, ondelete='cascade')
    stock_move_id = fields.Many2one('stock.move', string='Stock Move Line', ondelete='cascade')
    product_id = fields.Many2one('product.product', related="stock_move_id.product_id")
    product_uom_qty = fields.Float(string='Demand', default=0.0, related="stock_move_id.product_uom_qty")
    challan_qty = fields.Float(string='Challan Qty.', default=0.0, digits=(12, 1))


