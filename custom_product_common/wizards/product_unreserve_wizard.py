from odoo import exceptions, fields, models, _, api
from odoo.exceptions import UserError
import base64
import datetime, time
from odoo.addons.helper import validator


class ProductUnreserveWizard(models.TransientModel):
    _name = "product.unreserve.wizard"
    _description = "Product Unreserve Wizard"

    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one("stock.location", string='Location',domain="[('usage', '=', 'internal')]")
    quant_id = fields.Many2one("stock.quant")
    qty_available = fields.Float()
    qty_reserve = fields.Float()
    qty_unreserve = fields.Float()
    type = fields.Selection([
        ('01', 'Qty UnReserve'),
        ('02', 'Fix Qty Reserve'),
    ], string='Type', default='01')
    fixed_reserve = fields.Float()

    @api.onchange('product_id', 'location_id')
    def _onchange_product_id(self):
        if self.product_id and self.location_id:
            data_sql = """select id, quantity, reserved_quantity from stock_quant 
                          where location_id = %s and product_id = %s limit 1;
                        """ % (self.location_id.id, self.product_id.id)
            self.env.cr.execute(data_sql)
            data_res = self.env.cr.dictfetchall()
            if data_res:
                self.quant_id = data_res[0]['id']
                self.qty_available = data_res[0]['quantity']
                self.qty_reserve = data_res[0]['reserved_quantity']
            else:
                self.quant_id = None
                self.qty_available = 0
                self.qty_reserve = 0

    def action_done(self):
        if self.type == '01':
            if self.qty_unreserve < 1:
                raise exceptions.ValidationError(_('No Qty UnReserve!'))
            if not self.qty_reserve:
                raise exceptions.ValidationError(_('No Qty Reserve!'))
            if self.qty_unreserve > self.qty_reserve:
                raise exceptions.ValidationError(_('Unreserve qty can not be greater than Qty Reserve!'))
            current_qty = self.qty_reserve - self.qty_unreserve
            query = """ UPDATE stock_quant SET reserved_quantity = %s WHERE id = %s"""
            self.env.cr.execute(query, [current_qty, self.quant_id.id])
        else:
            if self.fixed_reserve < 1:
                raise exceptions.ValidationError(_('No Qty!'))
            current_qty = self.fixed_reserve
            query = """ UPDATE stock_quant SET reserved_quantity = %s WHERE id = %s"""
            self.env.cr.execute(query, [current_qty, self.quant_id.id])
    #
    # def action_done_reserve(self):
    #     query = """ UPDATE stock_quant SET reserved_quantity = %s WHERE id = %s"""
    #     self.env.cr.execute(query, [current_qty, self.quant_id.id])



