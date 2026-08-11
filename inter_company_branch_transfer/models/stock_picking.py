# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        """Hook into the real completion of a picking (after any backorder
        wizard has been resolved) to keep linked Inter-Company Transfers
        synchronized: validating the source Delivery Order automatically
        applies matching quantities to the destination Receipt and
        validates it, and the transfer is auto-closed once both sides
        are done."""
        res = super()._action_done()
        self._sync_inter_company_transfer()
        return res

    def _sync_inter_company_transfer(self):
        Transfer = self.env['inter.company.transfer'].sudo()
        for picking in self:
            if picking.state != 'done':
                continue

            transfer = False
            if picking.sale_id:
                transfer = Transfer.search(
                    [('sale_order_id', '=', picking.sale_id.id)], limit=1)
            if not transfer and picking.purchase_id:
                transfer = Transfer.search(
                    [('purchase_order_id', '=', picking.purchase_id.id)], limit=1)
            if not transfer or transfer.state not in ('confirmed',):
                continue

            is_source_delivery = bool(picking.sale_id) and picking.sale_id == transfer.sale_order_id
            if is_source_delivery and transfer.sync_delivery_receipt:
                transfer._sync_receipt_from_delivery(picking)

            transfer._check_auto_done()
