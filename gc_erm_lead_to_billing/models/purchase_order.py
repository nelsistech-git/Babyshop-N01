# -*- coding: utf-8 -*-
"""Purchase integration for procurement requests (SRS 33)."""

from odoo import _, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    gc_procurement_id = fields.Many2one(
        'gc.erm.procurement.request', string='ERM Procurement Request',
        copy=False, index=True, ondelete='set null')
    gc_work_order_id = fields.Many2one(
        'gc.erm.work.order', string='ERM Work Order', copy=False, index=True,
        ondelete='set null')
    gc_customer_id = fields.Many2one(
        'res.partner', string='End Customer',
        related='gc_work_order_id.partner_id', store=True)

    def button_confirm(self):
        res = super().button_confirm()
        requests = self.mapped('gc_procurement_id')
        if requests:
            requests.action_mark_po_created()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        for order in self.filtered('gc_procurement_id'):
            order.gc_procurement_id.message_post(body=_(
                'Purchase order %s was cancelled.', order.name))
        return res

    def _prepare_picking(self):
        vals = super()._prepare_picking()
        if self.gc_work_order_id:
            vals['gc_work_order_id'] = self.gc_work_order_id.id
        return vals


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    gc_procurement_line_id = fields.Many2one(
        'gc.erm.procurement.line', string='ERM Procurement Line', copy=False,
        index=True, ondelete='set null')

    def write(self, vals):
        res = super().write(vals)
        if 'qty_received' in vals:
            requests = self.mapped('gc_procurement_line_id.request_id')
            if requests:
                requests.action_check_receipt()
        return res
