# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CctvPosLink(models.Model):
    """POS Integration: one row per POS order that ties the sale to the
    billing-counter camera watching that register at the moment of sale, so
    a manager can jump straight to that footage/snapshot if the transaction
    looks off. Created automatically on POS order validation (see
    pos_order_ext.py) and optionally enriched with a snapshot + any
    theft/suspicious cctv.event correlated by the AI service around the
    same timestamp."""
    _name = 'cctv.pos.link'
    _description = 'CCTV \u2194 POS Transaction Link'
    _order = 'order_time desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    pos_order_id = fields.Many2one('pos.order', required=True, ondelete='cascade')
    camera_id = fields.Many2one('cctv.camera', required=True)
    office_id = fields.Many2one(related='camera_id.office_id', store=True)
    cashier_id = fields.Many2one('res.users', string='Cashier')
    order_time = fields.Datetime(required=True, index=True)
    amount_total = fields.Monetary(related='pos_order_id.amount_total', store=True)
    currency_id = fields.Many2one(related='pos_order_id.currency_id', store=True)
    snapshot = fields.Binary(string='Counter Snapshot at Sale', attachment=True)
    event_id = fields.Many2one('cctv.event', string='Correlated Suspicious Event',
                                help='Auto-filled if the AI service raised a theft_suspected/'
                                     'item_concealment event on this camera within the '
                                     'correlation window around this transaction.')
    mismatch_flagged = fields.Boolean(
        string='Flagged for Review',
        help='Set automatically when a correlated suspicious event exists, or manually '
             'by a reviewer who spots a mismatch between the footage and the receipt.')
    review_notes = fields.Text()

    @api.depends('pos_order_id', 'order_time')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"POS {rec.pos_order_id.name or ''} @ {rec.camera_id.name or ''} " \
                                f"({rec.order_time or ''})"

    def action_view_camera_events(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Camera Events Around This Sale',
            'res_model': 'cctv.event',
            'view_mode': 'tree,form',
            'domain': [
                ('camera_id', '=', self.camera_id.id),
                ('event_time', '>=', fields.Datetime.to_string(
                    self.order_time - __import__('datetime').timedelta(minutes=5))),
                ('event_time', '<=', fields.Datetime.to_string(
                    self.order_time + __import__('datetime').timedelta(minutes=5))),
            ],
        }
