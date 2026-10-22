# -*- coding: utf-8 -*-
import datetime
from odoo import models, fields, api


class PosOrderExt(models.Model):
    """POS \u2194 CCTV sync: whenever a POS order is created against a register
    that has a camera linked (cctv.camera.is_pos_counter_camera +
    pos_config_id), auto-create a cctv.pos.link row time-stamped to the
    order, and pull in the nearest snapshot the AI service already has on
    file for that camera (from cctv.event within the last 60s) plus flag it
    if a theft/suspicious event landed on that camera in the same window."""
    _inherit = 'pos.order'

    cctv_link_ids = fields.One2many('cctv.pos.link', 'pos_order_id', string='CCTV Links')

    def _create_cctv_pos_links(self):
        Camera = self.env['cctv.camera'].sudo()
        Link = self.env['cctv.pos.link'].sudo()
        Event = self.env['cctv.event'].sudo()
        for order in self:
            if not order.config_id:
                continue
            cameras = Camera.search([
                ('is_pos_counter_camera', '=', True),
                ('pos_config_id', '=', order.config_id.id),
            ])
            for cam in cameras:
                order_time = order.date_order or fields.Datetime.now()
                window_start = order_time - datetime.timedelta(seconds=60)
                window_end = order_time + datetime.timedelta(seconds=60)
                nearby_snapshot_event = Event.search([
                    ('camera_id', '=', cam.id),
                    ('event_time', '>=', fields.Datetime.to_string(window_start)),
                    ('event_time', '<=', fields.Datetime.to_string(window_end)),
                    ('snapshot', '!=', False),
                ], limit=1, order='event_time desc')
                suspicious_event = Event.search([
                    ('camera_id', '=', cam.id),
                    ('behavior_type', 'in', ['theft_suspected', 'item_concealment']),
                    ('event_time', '>=', fields.Datetime.to_string(window_start)),
                    ('event_time', '<=', fields.Datetime.to_string(window_end)),
                ], limit=1, order='event_time desc')
                Link.create({
                    'pos_order_id': order.id,
                    'camera_id': cam.id,
                    'cashier_id': order.user_id.id,
                    'order_time': order_time,
                    'snapshot': nearby_snapshot_event.snapshot if nearby_snapshot_event else False,
                    'event_id': suspicious_event.id if suspicious_event else False,
                    'mismatch_flagged': bool(suspicious_event),
                })

    @api.model_create_multi
    def create(self, vals_list):
        # Overriding plain create() (rather than a POS-UI-specific sync
        # method) keeps this working regardless of Odoo version/POS
        # front-end sync mechanism - every order, from any source, passes
        # through create().
        orders = super().create(vals_list)
        try:
            orders._create_cctv_pos_links()
        except Exception:
            # Never let CCTV linking break a POS sale - log and move on.
            import logging
            logging.getLogger(__name__).exception('cctv_management: failed to create CCTV/POS link')
        return orders
