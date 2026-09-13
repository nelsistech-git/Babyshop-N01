# -*- coding: utf-8 -*-
"""Delivery and receipt integration (SRS 33 / 34 / 35)."""

from odoo import _, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    gc_work_order_id = fields.Many2one(
        'gc.erm.work.order', string='ERM Work Order', copy=False, index=True,
        ondelete='set null')
    gc_sale_order_id = fields.Many2one(
        'sale.order', string='ERM Sales Order', copy=False,
        ondelete='set null')
    gc_team_id = fields.Many2one(
        'gc.erm.team', string='Implementation Team', copy=False,
        ondelete='set null')
    gc_customer_id = fields.Many2one(
        'res.partner', string='End Customer',
        related='gc_work_order_id.partner_id', store=True)

    def button_validate(self):
        res = super().button_validate()
        done_pickings = self.filtered(lambda p: p.state == 'done')
        # Outgoing deliveries linked to a work order refresh its material state.
        work_orders = done_pickings.mapped('gc_work_order_id')
        for work_order in work_orders:
            work_order._compute_material_state()
            work_order._compute_billing_ready()
            work_order.message_post(body=_(
                'Materials delivered to the implementation team.'))
        # Incoming receipts feed the procurement requests back.
        requests = done_pickings.mapped(
            'move_ids.purchase_line_id.gc_procurement_line_id.request_id')
        if requests:
            requests.action_check_receipt()
        return res

    def action_gc_view_work_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gc.erm.work.order',
            'res_id': self.gc_work_order_id.id,
            'view_mode': 'form',
        }
