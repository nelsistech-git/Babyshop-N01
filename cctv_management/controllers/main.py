# -*- coding: utf-8 -*-
import base64
import json
import logging

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


def _check_api_key():
    """Shared-secret auth for the external AI service.
    Set the key once: Settings > Technical > System Parameters
    key: cctv_management.api_key
    Send it back as header: X-CCTV-API-KEY
    """
    expected = request.env['ir.config_parameter'].sudo().get_param('cctv_management.api_key')
    got = request.httprequest.headers.get('X-CCTV-API-KEY')
    return bool(expected) and got == expected


class CctvApiController(http.Controller):

    @http.route('/cctv/api/heartbeat', type='json', auth='public', methods=['POST'], csrf=False)
    def heartbeat(self, **kwargs):
        """External agent (or the camera's own ONVIF poller) calls this every ~60s
        with {"camera_code": "CAM-0001"} to mark a camera online."""
        if not _check_api_key():
            return {'error': 'unauthorized'}
        payload = json.loads(request.httprequest.data or b'{}')
        camera_code = payload.get('camera_code')
        camera = request.env['cctv.camera'].sudo().search([('camera_code', '=', camera_code)], limit=1)
        if not camera:
            return {'error': 'camera_not_found'}
        camera.action_mark_online()
        return {'status': 'ok', 'camera_id': camera.id}

    @http.route('/cctv/api/config', type='json', auth='public', methods=['POST'], csrf=False)
    def ai_config(self, **kwargs):
        """AI service pulls its whole configuration (cameras, capabilities, models, thresholds).
        Body: {"have_version": "<hash>"}  ->  {"changed": false} when nothing changed."""
        if not _check_api_key():
            return {'error': 'unauthorized'}
        payload = json.loads(request.httprequest.data or b'{}')
        data = request.env['cctv.ai.config'].sudo().build()
        if payload.get('have_version') and payload['have_version'] == data['version']:
            return {'changed': False, 'version': data['version']}
        return {'changed': True, **data}

    @http.route('/cctv/api/ai_status', type='json', auth='public', methods=['POST'], csrf=False)
    def ai_status(self, **kwargs):
        """AI service reports each camera worker's state: {"cameras": {"CAM-0001": "running"}}.
        Also counts as a heartbeat for running workers."""
        if not _check_api_key():
            return {'error': 'unauthorized'}
        payload = json.loads(request.httprequest.data or b'{}')
        cams = payload.get('cameras') or {}
        env = request.env
        env['cctv.camera'].sudo().register_ai_status(cams)
        for code, status in cams.items():
            if status == 'running':
                cam = env['cctv.camera'].sudo().search([('camera_code', '=', code)], limit=1)
                if cam:
                    cam.action_mark_online()
        return {'status': 'ok', 'count': len(cams)}

    @http.route('/cctv/api/event', type='json', auth='public', methods=['POST'], csrf=False)
    def push_event(self, **kwargs):
        """External AI service (YOLO/DeepSORT/InsightFace/ANPR) posts detections here.

        Expected JSON body, e.g.:
        {
          "camera_code": "CAM-0001",
          "detection_type": "human",       # human|vehicle|face|animal|fire|smoke
          "behavior_type": "loitering",    # optional, see cctv.event selection
          "confidence": 92.5,
          "bounding_box": {"x":10,"y":20,"w":100,"h":220},
          "track_id": 7,                    # optional, tracker id (Live Monitor: one box per person)
          "frame_size": {"w":640,"h":480},  # optional, frame the bounding box was measured in
          "snapshot_base64": "....",        # optional JPEG, base64
          "source_service": "yolo-v8-cam01",
          "event_time": "2026-08-02T10:15:00",   # optional, defaults to now
          "vehicle": {"license_plate": "DHA-1234", "vehicle_type": "car"},  # optional
          "face_match": {"person_id": 17, "confidence": 88.0, "is_unknown": false}  # optional
        }
        """
        if not _check_api_key():
            return {'error': 'unauthorized'}

        payload = json.loads(request.httprequest.data or b'{}')
        env = request.env
        camera = env['cctv.camera'].sudo().search(
            [('camera_code', '=', payload.get('camera_code'))], limit=1)
        if not camera:
            return {'error': 'camera_not_found'}

        vals = {
            'camera_id': camera.id,
            'detection_type': payload.get('detection_type', 'human'),
            'behavior_type': payload.get('behavior_type', 'none'),
            'confidence': payload.get('confidence', 0.0),
            'bounding_box': json.dumps(payload.get('bounding_box')) if payload.get('bounding_box') else False,
            'source_service': payload.get('source_service'),
            'raw_payload': json.dumps(payload),
        }
        # Live Monitor overlay support (optional): tracker id + the frame size the box was measured in
        if payload.get('track_id') not in (None, ''):
            vals['track_ref'] = str(payload['track_id'])[:32]
        frame = payload.get('frame_size') or {}
        if frame.get('w') and frame.get('h'):
            vals['frame_width'] = int(frame['w'])
            vals['frame_height'] = int(frame['h'])
        if payload.get('event_time'):
            vals['event_time'] = payload['event_time'].replace('T', ' ')[:19]
        if payload.get('snapshot_base64'):
            vals['snapshot'] = payload['snapshot_base64']

        vehicle = payload.get('vehicle')
        if vehicle and vehicle.get('license_plate'):
            # entry/exit bookkeeping + owner/visit linking (see cctv_vehicle_ext.py)
            vlog = env['cctv.vehicle.log'].sudo().register_plate(
                camera, vehicle['license_plate'], vehicle.get('vehicle_type', 'car'),
                vehicle.get('speed_kph', 0.0))
            vals['vehicle_log_id'] = vlog.id
            vals['detection_type'] = 'vehicle'
            if vlog.visit_id:
                vals['visit_id'] = vlog.visit_id.id      # gate sighting becomes part of the visit's route

        face_match = payload.get('face_match')
        if face_match:
            person_id = face_match.get('person_id')
            env['cctv.face.log'].sudo().create({
                'camera_id': camera.id,
                'person_id': person_id,
                'is_unknown': face_match.get('is_unknown', not bool(person_id)),
                'match_confidence': face_match.get('confidence', 0.0),
            })
            if person_id:
                vals['person_id'] = person_id
                person = env['cctv.person'].sudo().browse(int(person_id)).exists()
                if person:
                    person._note_sighting(camera)
                    visit = env['cctv.visit'].sudo().register_face_sighting(camera, person)
                    if visit:
                        vals['visit_id'] = visit.id      # camera-to-camera route tracking
                    person._raise_watchlist_alert(camera)   # blacklisted -> critical, VIP -> heads-up
            vals['detection_type'] = 'face'
            if not person_id:
                env['cctv.alert'].sudo().create({
                    'name': 'Unknown Face Detected - %s' % camera.name,
                    'alert_type': 'unknown_face',
                    'camera_id': camera.id,
                    'office_id': camera.office_id.id,
                    'severity': 'medium',
                })

        event = env['cctv.event'].sudo().create(vals)
        return {'status': 'ok', 'event_id': event.id, 'alert_id': event.alert_id.id or False,
                'incident_id': event.incident_id.id or False}

    @http.route('/cctv/api/people_count', type='json', auth='public', methods=['POST'], csrf=False)
    def people_count(self, **kwargs):
        """AI service pushes one row per camera per counting interval (people_counter.py).

        Body: {"camera_code": "CAM-0001", "interval_start": "...", "interval_end": "...",
               "entry_count": 4, "exit_count": 2, "net_inside": 11}
        """
        if not _check_api_key():
            return {'error': 'unauthorized'}
        payload = json.loads(request.httprequest.data or b'{}')
        env = request.env
        camera = env['cctv.camera'].sudo().search(
            [('camera_code', '=', payload.get('camera_code'))], limit=1)
        if not camera:
            return {'error': 'camera_not_found'}
        rec = env['cctv.footfall.count'].sudo().create({
            'camera_id': camera.id,
            'interval_start': (payload.get('interval_start') or '').replace('T', ' ')[:19] or fields.Datetime.now(),
            'interval_end': (payload.get('interval_end') or '').replace('T', ' ')[:19] or fields.Datetime.now(),
            'entry_count': payload.get('entry_count', 0),
            'exit_count': payload.get('exit_count', 0),
            'net_inside': payload.get('net_inside', 0),
        })
        return {'status': 'ok', 'footfall_id': rec.id}

    @http.route('/cctv/api/heatmap', type='json', auth='public', methods=['POST'], csrf=False)
    def heatmap(self, **kwargs):
        """AI service pushes one rendered heatmap + zone stats per accumulation
        period (heatmap.py). snapshot/reference images are base64 JPEG/PNG.

        Body: {"camera_code": "CAM-0001", "period_start": "...", "period_end": "...",
               "heatmap_image_base64": "...", "reference_frame_base64": "...",
               "zone_stats": {"Rack A": {"visits": 40, "avg_dwell_seconds": 35, "share_pct": 22.5}},
               "total_detections": 180}
        """
        if not _check_api_key():
            return {'error': 'unauthorized'}
        payload = json.loads(request.httprequest.data or b'{}')
        env = request.env
        camera = env['cctv.camera'].sudo().search(
            [('camera_code', '=', payload.get('camera_code'))], limit=1)
        if not camera:
            return {'error': 'camera_not_found'}
        vals = {
            'camera_id': camera.id,
            'period_start': (payload.get('period_start') or '').replace('T', ' ')[:19] or fields.Datetime.now(),
            'period_end': (payload.get('period_end') or '').replace('T', ' ')[:19] or fields.Datetime.now(),
            'zone_stats_json': json.dumps(payload.get('zone_stats')) if payload.get('zone_stats') else False,
            'total_detections': payload.get('total_detections', 0),
        }
        if payload.get('heatmap_image_base64'):
            vals['heatmap_image'] = payload['heatmap_image_base64']
        if payload.get('reference_frame_base64'):
            vals['reference_frame'] = payload['reference_frame_base64']
        rec = env['cctv.heatmap.snapshot'].sudo().create(vals)
        return {'status': 'ok', 'heatmap_id': rec.id}

    @http.route('/cctv/api/queue', type='json', auth='public', methods=['POST'], csrf=False)
    def queue_status(self, **kwargs):
        """AI service pushes a live queue reading (queue_monitor.py), typically
        every 15-30s for cameras flagged is_queue_zone_camera=True on cctv.camera.

        Body: {"camera_code": "CAM-0001", "person_count": 6, "avg_wait_seconds": 90,
               "threshold": 5}
        """
        if not _check_api_key():
            return {'error': 'unauthorized'}
        payload = json.loads(request.httprequest.data or b'{}')
        env = request.env
        camera = env['cctv.camera'].sudo().search(
            [('camera_code', '=', payload.get('camera_code'))], limit=1)
        if not camera:
            return {'error': 'camera_not_found'}
        threshold = payload.get('threshold', 5)
        person_count = payload.get('person_count', 0)
        overcrowded = person_count > threshold
        rec = env['cctv.queue.status'].sudo().create({
            'camera_id': camera.id,
            'person_count': person_count,
            'avg_wait_seconds': payload.get('avg_wait_seconds', 0),
            'threshold_used': threshold,
            'is_overcrowded': overcrowded,
        })
        if overcrowded:
            env['cctv.event'].sudo().create({
                'camera_id': camera.id,
                'detection_type': 'human',
                'behavior_type': 'queue_overcrowded',
                'confidence': 100.0,
                'source_service': 'cctv-ai-service-queue',
            })
        return {'status': 'ok', 'queue_status_id': rec.id, 'is_overcrowded': overcrowded}
