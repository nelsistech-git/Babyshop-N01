from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.helper import validator


class StockMoveInherit(models.Model):
    _inherit = 'stock.move'
    _description = "Stock Move Inherit"

    challan_qty = fields.Float(string='Challan Qty.', default=0.0, copy=False, digits='Product Unit of Measure')
    expiry_date = fields.Date(string='Expiry Date')
    available_stock = fields.Float(string='On Hand Stock', compute='_compute_available_stock', digits='Product Unit of Measure')
    remarks = fields.Char(string="Remarks")

    # @api.constrains('product_id', 'picking_id')
    # def _check_unique_constraint(self):
    #     for rec in self:
    #         msg = "%s" % rec.product_id.display_name
    #         envobj = self.env['stock.move']
    #         if rec.picking_id:
    #             if not self.env.context.get('button_name'):
    #                 conditionlist = [('picking_id', '=', rec.picking_id.id), ('product_id', '=', rec.product_id.id)]
    #                 validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.onchange('product_id')
    def _compute_available_stock(self):
        for rec in self:
            if rec.picking_id:
                if rec.picking_id.purchase_id:
                    if rec.product_id:
                        available_qty = rec.product_id.with_context({'location': rec.picking_id.location_dest_id.id}).qty_available
                        rec.available_stock = available_qty
                    else:
                        rec.available_stock = 0
                else:
                    if rec.product_id:
                        available_qty = rec.product_id.with_context({'location': rec.picking_id.location_id.id}).qty_available
                        rec.available_stock = available_qty
                    else:
                        rec.available_stock = 0


class StockReturnPickingInheritCustomStock(models.TransientModel):
    _inherit = 'stock.return.picking'

    type = fields.Selection([
        ('1', 'All Product'),
        ('0', 'Barcode Scan')
    ], string='Type', copy=False, default='1')
    barcode_list = fields.Text(string="Barcode Scan")
    return_reason = fields.Text(string="Return Reason")
    location_id = fields.Many2one('stock.location', related='picking_id.location_id')
    location_dest_id = fields.Many2one('stock.location', related='picking_id.location_dest_id')




    # @api.onchange('picking_id', 'type')
    # def _onchange_picking_id(self):
    #     move_dest_exists = False
    #     product_return_moves = [(5,)]
    #     if self.picking_id and self.picking_id.state != 'done':
    #         raise UserError(_("You may only return Done pickings."))
    #     # In case we want to set specific default values (e.g. 'to_refund'), we must fetch the
    #     # default values for creation.
    #     line_fields = [f for f in self.env['stock.return.picking.line']._fields.keys()]
    #     product_return_moves_data_tmpl = self.env['stock.return.picking.line'].default_get(line_fields)
    #     for move in self.picking_id.move_ids_without_package:
    #         if move.state == 'cancel':
    #             continue
    #         if move.scrapped:
    #             continue
    #         if move.move_dest_ids:
    #             move_dest_exists = True
    #         product_return_moves_data = dict(product_return_moves_data_tmpl)
    #         product_return_moves_data.update(self._prepare_stock_return_picking_line_vals_from_move(move))
    #         product_return_moves.append((0, 0, product_return_moves_data))
    #     if self.picking_id and not product_return_moves:
    #         raise UserError(
    #             _("No products to return (only lines in Done state and not fully returned yet can be returned)."))
    #     if self.picking_id:
    #         if self.type == '1':
    #             self.product_return_moves = product_return_moves
    #         else:
    #             self.product_return_moves = None
    #         self.move_dest_exists = move_dest_exists
    #         self.parent_location_id = self.picking_id.picking_type_id.warehouse_id and self.picking_id.picking_type_id.warehouse_id.view_location_id.id or self.picking_id.location_id.location_id.id
    #         self.original_location_id = self.picking_id.location_id.id
    #         location_id = self.picking_id.location_id.id
    #         if self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
    #             location_id = self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.id
    #         self.location_id = location_id

    def barcode_scan(self):
        if self.barcode_list:
            self.product_return_moves = None
            pro_ids = [line.product_id.id for line in self.picking_id.move_ids_without_package]
            pro_lines = []
            barcode_list = self.barcode_list.split('\n')
            for rec in barcode_list:
                product_obj = self.env['product.product'].search([('product_code', '=', rec)], limit=1)
                if product_obj.id not in pro_ids:
                    product_obj = self.env['product.product'].search([('barcode', '=', rec)], limit=1)
                    if product_obj.id not in pro_ids:
                        raise UserError(
                            _("%s This Barcode does not exist in this Transfer.")%(rec))

                if product_obj:
                    move_id = self.env['stock.move'].search([('product_id', '=', product_obj.id), ('picking_id', '=', self.picking_id.id)])
                    pro_dict = {
                        'product_id': product_obj.id,
                        'quantity': move_id.product_uom_qty,
                        'uom_id': product_obj.uom_id.id,
                        'move_id': move_id.id,
                    }
                    pro_lines.append((0, 0, pro_dict))
            self.product_return_moves = pro_lines

            return {
                'name': _('Reverse Transfer'),
                'context': self.env.context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.return.picking',
                'res_id': self.id,
                'view_id': False,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    def create_returns(self):
        res = super(StockReturnPickingInheritCustomStock, self).create_returns()
        if res:
            picking_obj = self.env['stock.picking']
            return_pickings = picking_obj.browse([res['res_id']])
            return_pickings.return_reason = self.return_reason

            return res
