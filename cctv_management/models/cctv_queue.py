# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CctvQueueStatus(models.Model):
    """Live/periodic billing-counter crowding reading, pushed by the AI
    service's queue_monitor.py via POST /cctv/api/queue. When person_count
    exceeds the camera's configured threshold for longer than the configured
    duration, the AI service (or this model's cron) raises a
    'queue_overcrowded' cctv.event/alert so staff can open another counter."""
    _name = 'cctv.queue.status'
    _description = 'Queue / Billing Counter Monitoring'
    _order = 'reading_time desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    camera_id = fields.Many2one('cctv.camera', required=True, ondelete='cascade')
    office_id = fields.Many2one(related='camera_id.office_id', store=True)
    reading_time = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    person_count = fields.Integer(string='People in Queue', default=0)
    avg_wait_seconds = fields.Integer(string='Estimated Avg Wait (s)', default=0)
    is_overcrowded = fields.Boolean(default=False)
    threshold_used = fields.Integer(string='Threshold Applied')

    @api.depends('camera_id', 'reading_time', 'person_count')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.camera_id.name or ''}] {rec.person_count} in queue ({rec.reading_time or ''})"

    @api.model
    def current_status(self, office_id=False):
        """Latest reading per queue camera - used by the Real-Time Dashboard tile."""
        domain = [('camera_id.is_queue_zone_camera', '=', True)]
        if office_id:
            domain.append(('office_id', '=', office_id))
        cameras = self.env['cctv.camera'].search(
            [('is_queue_zone_camera', '=', True)] + ([('office_id', '=', office_id)] if office_id else []))
        result = []
        for cam in cameras:
            latest = self.search([('camera_id', '=', cam.id)], limit=1, order='reading_time desc')
            result.append({
                'camera': cam.name,
                'person_count': latest.person_count if latest else 0,
                'is_overcrowded': latest.is_overcrowded if latest else False,
                'reading_time': latest.reading_time if latest else False,
            })
        return result
