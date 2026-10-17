# -*- coding: utf-8 -*-
from odoo import api, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        mapping = self.env.context.get('bond_po_line_map')
        if mapping:
            origin = self.env.context.get('bond_po_origin')
            Line = self.env['purchase.order.line'].sudo()
            for vals in vals_list:
                if vals.get('purchase_line_id') or vals.get('origin') != origin:
                    continue
                pol_id = mapping.get('%s:%s' % (vals.get('product_id'), vals.get('product_uom')))
                if pol_id:
                    vals['purchase_line_id'] = pol_id
                    vals['price_unit'] = Line.browse(pol_id)._get_stock_move_price_unit()
        return super().create(vals_list)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model_create_multi
    def create(self, vals_list):
        Receipt = self.env['bond.inventory.receipt'].sudo()
        for vals in vals_list:
            if vals.get('bond_receipt_id'):
                refs = Receipt.browse(vals['bond_receipt_id'])._bond_picking_refs()
                for fname, value in refs.items():
                    if value and not vals.get(fname):
                        vals[fname] = value
        return super().create(vals_list)
