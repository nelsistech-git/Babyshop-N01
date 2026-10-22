# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CctvHeatmapSnapshot(models.Model):
    """A rendered heatmap image + per-zone dwell/traffic stats for one camera
    over one accumulation period (default: hourly). Pushed by the AI
    service's heatmap.py accumulator via POST /cctv/api/heatmap.
    Powers 'popular areas/racks' analytics for showrooms."""
    _name = 'cctv.heatmap.snapshot'
    _description = 'Heatmap Analytics Snapshot'
    _order = 'period_start desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    camera_id = fields.Many2one('cctv.camera', required=True, ondelete='cascade')
    office_id = fields.Many2one(related='camera_id.office_id', store=True)
    department_id = fields.Many2one(related='camera_id.department_id', store=True)
    period_start = fields.Datetime(required=True, index=True)
    period_end = fields.Datetime(required=True)
    heatmap_image = fields.Binary(string='Heatmap Overlay (PNG)', attachment=True,
                                   help='Semi-transparent red/yellow/green density overlay, '
                                        'meant to be shown on top of a reference frame of this camera.')
    reference_frame = fields.Binary(string='Reference Frame (JPEG)', attachment=True,
                                     help='One plain frame from the camera the overlay aligns to.')
    zone_stats_json = fields.Text(
        string='Zone Stats (JSON)',
        help='{"zone_name": {"visits": N, "avg_dwell_seconds": N, "share_pct": N}, ...} '
             'e.g. per-rack/per-shelf traffic breakdown, if zones were configured for this camera.')
    hottest_zone = fields.Char(string='Most Popular Zone', compute='_compute_hottest_zone', store=True)
    total_detections = fields.Integer(default=0)

    @api.depends('camera_id', 'period_start')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.camera_id.name or ''}] Heatmap ({rec.period_start or ''})"

    @api.depends('zone_stats_json')
    def _compute_hottest_zone(self):
        import json
        for rec in self:
            rec.hottest_zone = False
            if not rec.zone_stats_json:
                continue
            try:
                stats = json.loads(rec.zone_stats_json)
                if stats:
                    rec.hottest_zone = max(stats.items(), key=lambda kv: kv[1].get('visits', 0))[0]
            except (ValueError, TypeError):
                pass
