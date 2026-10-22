# -*- coding: utf-8 -*-
"""v4.0 camera extensions: recording playback, loading-bay / ERP link, gate direction."""
from datetime import timedelta, timezone

from odoo import api, fields, models


class CctvCameraV4(models.Model):
    _inherit = 'cctv.camera'

    # ---- Recording playback (SRS feature 10: jump to the relevant clip)
    playback_url_template = fields.Char(
        string='Playback URL Template',
        help='URL of your recording/playback server for a time window. Placeholders: {path} {camera_code} '
             '{start_iso} {end_iso} {start_epoch} {end_epoch} {duration}. '
             'MediaMTX example: http://NVR_HOST:9996/get?path={path}&start={start_iso}&duration={duration}')
    playback_stream_path = fields.Char(
        string='Playback Stream Path',
        help='Path name of this camera on the recording server (MediaMTX path, e.g. cam0001). '
             'Defaults to the camera code without dashes, lower-case.')
    playback_preroll_seconds = fields.Integer(string='Clip Pre-roll (s)', default=10)
    playback_clip_seconds = fields.Integer(string='Clip Length (s)', default=40)

    # ---- Warehouse / ERP link (SRS feature 5)
    is_loading_bay_camera = fields.Boolean(
        string='Loading Bay / Goods Camera',
        help='Goods and forklift movements seen by this camera are matched against stock transfers '
             '(stock.picking) of the warehouse below. CCTV evidence only: it cannot count stock quantities.')
    warehouse_id = fields.Many2one('stock.warehouse', string='ERP Warehouse')

    # ---- Vehicle gates / parking (SRS feature 8)
    vehicle_direction = fields.Selection([
        ('entry', 'Entry gate'), ('exit', 'Exit gate'), ('both', 'Single gate (in and out)'),
    ], default='entry', string='Gate Direction',
        help='Used by ANPR: a plate seen on an exit gate closes its open parking/visit record.')

    stock_link_ids = fields.One2many('cctv.stock.link', 'camera_id', string='ERP Links')

    def _playback_url_for(self, when):
        """Build the playback URL for a UTC datetime, or False if not configured."""
        self.ensure_one()
        template = self.playback_url_template
        if not template:
            base = (self.env['ir.config_parameter'].sudo().get_param('cctv_management.playback_base_url') or '').rstrip('/')
            if base:
                template = base + '/get?path={path}&start={start_iso}&duration={duration}'
        if not template or not when:
            return False
        start = when - timedelta(seconds=self.playback_preroll_seconds or 0)
        end = start + timedelta(seconds=self.playback_clip_seconds or 40)
        path = self.playback_stream_path or (self.camera_code or '').replace('-', '').lower()
        values = {
            'path': path, 'camera_code': self.camera_code or '',
            'start_iso': start.strftime('%Y-%m-%dT%H:%M:%SZ'), 'end_iso': end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'start_epoch': int(start.replace(tzinfo=timezone.utc).timestamp()),
            'end_epoch': int(end.replace(tzinfo=timezone.utc).timestamp()),
            'duration': self.playback_clip_seconds or 40,
        }
        url = template
        for k, v in values.items():
            url = url.replace('{%s}' % k, str(v))
        return url

    # ------------------------------------------------------------------
    # Live Monitor: per-camera tracking snapshot (polled every few seconds)
    # ------------------------------------------------------------------
    _LIVE_NORMAL_BEHAVIORS = ('none', False)

    @api.model
    def get_live_tracking(self, camera_ids, window_seconds=8, include_counters=False):
        """Everything the Live Monitor overlay needs, in ONE call for all visible cameras.

        Colour rule (tracking areas): GREEN = tracked and behaving normally,
        RED = flagged (any behaviour other than 'none', fire/smoke/tamper).

        Returns {camera_id: {health_status, frame_w, frame_h, tracks[], green, red, people,
                             alerts[], queue?, footfall?}}
        - tracks: the live boxes (latest event per tracker id inside the last `window_seconds`)
        - alerts: distinct flagged events of the last 5 minutes (newest first, max 5)
        - queue / footfall: only when include_counters=True (the slow part; JS asks every ~15s)
        """
        import json as _json
        cams = self.browse(camera_ids).exists()
        if not cams:
            return {}
        Event = self.env['cctv.event']
        behavior_label = dict(Event._fields['behavior_type'].selection)
        now = fields.Datetime.now()
        since = now - timedelta(seconds=max(2, min(int(window_seconds), 60)))

        result = {}
        for cam in cams:
            result[cam.id] = {
                'health_status': cam.health_status, 'frame_w': 0, 'frame_h': 0,
                'tracks': [], 'green': 0, 'red': 0, 'people': 0, 'alerts': [],
                'caps': [c for c in (cam.ai_capability_labels or '').split(' · ') if c],
                'ai_state': cam.ai_state,
                'drive': bool(cam.drive_enabled),
            }

        # ---- live tracks: newest events only, one per tracker id ----
        live = Event.search([('camera_id', 'in', cams.ids), ('event_time', '>=', since)],
                            order='event_time desc, id desc', limit=60 * len(cams))
        seen = set()
        newest = {}
        for ev in live:
            cid = ev.camera_id.id
            newest.setdefault(cid, ev.event_time)
            data = result[cid]
            if ev.track_ref:
                key = (cid, 'trk', ev.detection_type, ev.track_ref)
            else:
                # no tracker id: only trust the newest "frame batch" (events within 1.5 s of the latest)
                if (newest[cid] - ev.event_time).total_seconds() > 1.5:
                    continue
                key = (cid, 'ev', ev.id)
            if key in seen:
                continue
            seen.add(key)
            try:
                box = _json.loads(ev.bounding_box) if ev.bounding_box else None
            except ValueError:
                box = None
            flagged = (ev.behavior_type not in self._LIVE_NORMAL_BEHAVIORS
                       or ev.detection_type in ('fire', 'smoke', 'tamper'))
            if ev.frame_width and ev.frame_height:
                data['frame_w'], data['frame_h'] = ev.frame_width, ev.frame_height
            data['green' if not flagged else 'red'] += 1
            if ev.detection_type == 'human':
                data['people'] += 1
            if box and all(k in box for k in ('x', 'y', 'w', 'h')):
                label = behavior_label.get(ev.behavior_type) if flagged and ev.behavior_type != 'none' \
                    else dict(Event._fields['detection_type'].selection).get(ev.detection_type, '')
                data['tracks'].append({
                    'id': ev.track_ref or str(ev.id),
                    'color': 'red' if flagged else 'green',
                    'label': label or '',
                    'det': ev.detection_type,
                    'conf': round(ev.confidence or 0),
                    'x': box['x'], 'y': box['y'], 'w': box['w'], 'h': box['h'],
                })

        # ---- recent flagged events (distinct), for the corner panel / fullscreen list ----
        recent = Event.search([
            ('camera_id', 'in', cams.ids),
            ('event_time', '>=', now - timedelta(minutes=5)),
            '|', ('behavior_type', 'not in', ['none']), ('detection_type', 'in', ['fire', 'smoke', 'tamper']),
        ], order='event_time desc, id desc', limit=40 * len(cams))
        alert_seen = set()
        for ev in recent:
            data = result[ev.camera_id.id]
            if len(data['alerts']) >= 5:
                continue
            key = (ev.camera_id.id, ev.behavior_type, ev.detection_type, ev.track_ref or '')
            if key in alert_seen:
                continue
            alert_seen.add(key)
            data['alerts'].append({
                'label': behavior_label.get(ev.behavior_type) if ev.behavior_type != 'none'
                else dict(Event._fields['detection_type'].selection).get(ev.detection_type, ''),
                'age': int((now - ev.event_time).total_seconds()),
            })

        # ---- slow counters (queue length, today's footfall) ----
        if include_counters:
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            counter_cams = cams.filtered(lambda c: c.ai_people_counting or c.is_entry_exit_camera)
            if counter_cams:
                groups = self.env['cctv.footfall.count'].read_group(
                    [('camera_id', 'in', counter_cams.ids), ('interval_start', '>=', today)],
                    ['entry_count:sum', 'exit_count:sum'], ['camera_id'])
                for g in groups:
                    cid = g['camera_id'][0]
                    entries, exits = g['entry_count'] or 0, g['exit_count'] or 0
                    result[cid]['footfall'] = {'in': entries, 'out': exits, 'inside': max(entries - exits, 0)}
            for cam in cams.filtered('is_queue_zone_camera'):
                last = self.env['cctv.queue.status'].search(
                    [('camera_id', '=', cam.id)], limit=1, order='reading_time desc')
                if last:
                    result[cam.id]['queue'] = {
                        'count': last.person_count, 'wait': last.avg_wait_seconds,
                        'over': last.is_overcrowded,
                        'age': int((now - last.reading_time).total_seconds()),
                    }
        return result
