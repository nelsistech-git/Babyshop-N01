# -*- coding: utf-8 -*-
"""CCTV <-> ERP inventory link for warehouse / loading-bay areas (SRS feature 5).

What it does:
  * every validated incoming/outgoing stock transfer of a warehouse is linked to the
    loading-bay camera(s) of that warehouse, with the latest snapshot as visual proof;
  * every goods/forklift/package movement the AI sees at a loading bay is held as
    'pending' and, after a grace period, matched against transfers in a time window.
    No matching transfer => the movement is flagged and an alert is raised.

What it does NOT do: count stock. CCTV cannot reliably tell quantities - the link
is evidence ("something moved here at 22:10 with no transfer"), never a stock number.
"""
from datetime import timedelta

from odoo import api, fields, models

MOVEMENT_BEHAVIORS = ('package_removal', 'forklift_movement', 'after_hours_presence')


class CctvStockLink(models.Model):
    _name = 'cctv.stock.link'
    _description = 'CCTV <-> Stock Transfer Link'
    _inherit = ['mail.thread']
    _order = 'event_time desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    camera_id = fields.Many2one('cctv.camera', required=True, ondelete='cascade', index=True)
    office_id = fields.Many2one(related='camera_id.office_id', store=True)
    warehouse_id = fields.Many2one('stock.warehouse', related='camera_id.warehouse_id', store=True)
    picking_id = fields.Many2one('stock.picking', ondelete='set null', index=True, tracking=True)
    event_id = fields.Many2one('cctv.event', ondelete='set null')
    link_type = fields.Selection([
        ('transfer', 'Stock transfer validated (bay snapshot)'),
        ('movement', 'Goods movement seen by camera'),
    ], required=True)
    event_time = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    match_state = fields.Selection([
        ('na', 'n/a'), ('pending', 'Waiting for matching transfer'),
        ('matched', 'Matched to a transfer'), ('unmatched', 'No matching transfer'),
    ], default='na', tracking=True, index=True)
    flagged = fields.Boolean(compute='_compute_flagged', store=True)
    snapshot = fields.Binary(attachment=True)
    notes = fields.Text()
    reviewed = fields.Boolean(tracking=True)

    @api.depends('link_type', 'event_id', 'picking_id', 'event_time', 'camera_id')
    def _compute_name(self):
        for rec in self:
            ref = rec.picking_id.name or (rec.event_id.display_name if rec.event_id else '')
            rec.name = '%s | %s | %s' % (rec.camera_id.name or '', dict(
                rec._fields['link_type'].selection).get(rec.link_type, ''), ref or '-')

    @api.depends('match_state')
    def _compute_flagged(self):
        for rec in self:
            rec.flagged = rec.match_state == 'unmatched'

    def action_mark_reviewed(self):
        self.write({'reviewed': True})

    # ------------------------------------------------------------------ hooks
    @api.model
    def _grace_minutes(self):
        val = self.env['ir.config_parameter'].sudo().get_param('cctv_management.goods_match_minutes', '60')
        try:
            return max(5, int(val))
        except ValueError:
            return 60

    @api.model
    def _register_movement_event(self, event):
        """Called for every new cctv.event."""
        if event.behavior_type not in MOVEMENT_BEHAVIORS:
            return
        camera = event.camera_id
        if camera.is_loading_bay_camera and camera.warehouse_id:
            self.sudo().create({
                'camera_id': camera.id, 'event_id': event.id, 'link_type': 'movement',
                'event_time': event.event_time, 'match_state': 'pending', 'snapshot': event.snapshot,
            })
        elif event.behavior_type == 'package_removal':
            # no ERP context for this camera: nothing to match against, alert straight away
            self.env['cctv.alert'].sudo().create({
                'name': 'Package removal - %s' % camera.name, 'alert_type': 'other', 'severity': 'high',
                'camera_id': camera.id, 'office_id': camera.office_id.id, 'event_id': event.id})

    @api.model
    def cron_reconcile_movements(self):
        """Match pending movements to stock transfers once the grace period has passed."""
        grace = self._grace_minutes()
        cutoff = fields.Datetime.now() - timedelta(minutes=grace)
        Picking = self.env['stock.picking'].sudo()
        for link in self.search([('match_state', '=', 'pending'), ('event_time', '<=', cutoff)]):
            lo = link.event_time - timedelta(minutes=grace)
            hi = link.event_time + timedelta(minutes=grace)
            wh = link.camera_id.warehouse_id
            domain = [
                ('picking_type_id.warehouse_id', '=', wh.id),
                ('picking_type_code', 'in', ('incoming', 'outgoing', 'internal')),
                '|',
                '&', ('state', '=', 'done'), '&', ('date_done', '>=', lo), ('date_done', '<=', hi),
                '&', ('state', 'in', ('assigned', 'confirmed')), '&',
                ('scheduled_date', '>=', lo), ('scheduled_date', '<=', hi),
            ]
            picking = Picking.search(domain, limit=1, order='date_done desc, scheduled_date desc')
            if picking:
                link.write({'match_state': 'matched', 'picking_id': picking.id})
                continue
            link.write({'match_state': 'unmatched'})
            ev = link.event_id
            self.env['cctv.alert'].sudo().create({
                'name': 'Goods movement without a stock transfer - %s' % link.camera_id.name,
                'alert_type': 'other', 'severity': 'high',
                'camera_id': link.camera_id.id, 'office_id': link.office_id.id,
                'event_id': ev.id if ev else False,
                'notes': 'No stock transfer for warehouse %s within +/-%d min of %s. CCTV cannot tell '
                         'quantities; check the footage and the transfer records.'
                         % (wh.display_name, grace, link.event_time),
            })


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    cctv_link_ids = fields.One2many('cctv.stock.link', 'picking_id', string='CCTV Links')
    cctv_link_count = fields.Integer(compute='_compute_cctv_link_count')

    @api.depends('cctv_link_ids')
    def _compute_cctv_link_count(self):
        for rec in self:
            rec.cctv_link_count = len(rec.cctv_link_ids)

    def action_view_cctv_links(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': 'CCTV Evidence', 'res_model': 'cctv.stock.link',
                'view_mode': 'tree,form', 'domain': [('picking_id', '=', self.id)]}

    def _action_done(self):
        res = super()._action_done()
        try:
            self._cctv_link_validated()
        except Exception:   # noqa: BLE001 - CCTV evidence must never block a stock validation
            import logging
            logging.getLogger(__name__).exception('CCTV link for stock.picking failed (ignored)')
        return res

    def _cctv_link_validated(self):
        Link = self.env['cctv.stock.link'].sudo()
        Camera = self.env['cctv.camera'].sudo()
        now = fields.Datetime.now()
        for pick in self:
            if pick.picking_type_code not in ('incoming', 'outgoing'):
                continue
            wh = pick.picking_type_id.warehouse_id
            if not wh:
                continue
            for cam in Camera.search([('is_loading_bay_camera', '=', True), ('warehouse_id', '=', wh.id)]):
                last = self.env['cctv.event'].sudo().search([
                    ('camera_id', '=', cam.id), ('snapshot', '!=', False),
                    ('event_time', '>=', now - timedelta(minutes=15))], limit=1)
                Link.create({'camera_id': cam.id, 'picking_id': pick.id, 'link_type': 'transfer',
                             'event_time': now, 'snapshot': last.snapshot if last else False,
                             'event_id': last.id if last else False})
