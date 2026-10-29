# -*- coding: utf-8 -*-
"""HTTP API used by the face-attendance service (same X-CCTV-API-KEY as /cctv/api/*).

Plain JSON over POST (no JSON-RPC envelope):
  /cctv/api/attendance/config   cameras flagged for attendance + thresholds
  /cctv/api/attendance/gallery  employees to recognise + their reference photos
  /cctv/api/attendance/image/<kind>/<id>   one reference photo (GET)
  /cctv/api/attendance/punch    a confirmed recognition (or an unknown face)
  /cctv/api/attendance/status   worker state + enrolment quality report
"""
import base64
import hmac
import json
import logging

from odoo import _, fields, http
from odoo.http import Response, request

from ..models.cctv_person_attendance import is_real_photo

_logger = logging.getLogger(__name__)


def _json(data, status=200):
    return Response(json.dumps(data, default=str), status=status,
                    content_type='application/json;charset=utf-8')


def _authorized():
    expected = request.env['ir.config_parameter'].sudo().get_param('cctv_management.api_key')
    got = request.httprequest.headers.get('X-CCTV-API-KEY')
    return bool(expected) and bool(got) and hmac.compare_digest(str(expected), str(got))


def _body():
    try:
        return json.loads(request.httprequest.get_data(as_text=True) or '{}')
    except ValueError:
        return None


def _parse_time(value):
    if not value:
        return None
    try:
        return fields.Datetime.to_datetime(str(value).replace('T', ' ')[:19])
    except Exception:
        return None


class CctvAttendanceApi(http.Controller):

    def _guard(self):
        if not _authorized():
            return _json({'error': 'unauthorized'}, 401)
        return None

    @http.route('/cctv/api/attendance/config', type='http', auth='public', methods=['POST'], csrf=False)
    def config(self, **kw):
        denied = self._guard()
        if denied:
            return denied
        env = request.env
        cfg = env['cctv.attendance.config']
        cams = env['cctv.camera'].sudo().search([('ai_attendance', '=', True), ('active', '=', True)])
        payload = {'settings': cfg.service_settings(), 'cameras': [c.attendance_camera_config() for c in cams]}
        version = cfg.version_of(payload)
        body = _body() or {}
        if body.get('have_version') == version:
            return _json({'changed': False, 'version': version})
        return _json({'changed': True, 'version': version, 'server_time': fields.Datetime.now(), **payload})

    @http.route('/cctv/api/attendance/gallery', type='http', auth='public', methods=['POST'], csrf=False)
    def gallery(self, **kw):
        denied = self._guard()
        if denied:
            return denied
        env = request.env
        cfg = env['cctv.attendance.config']
        people, excluded = [], {}
        persons = env['cctv.person'].sudo().search([('person_type', '=', 'employee')])
        for person in persons:
            why = person._attendance_ineligible_reason()
            if why:
                excluded[why] = excluded.get(why, 0) + 1
                continue
            images = person._attendance_gallery_images()
            if not images:
                excluded[_('no photo')] = excluded.get(_('no photo'), 0) + 1
                if person.attendance_enroll_state != 'no_photo':
                    person.write({'attendance_enroll_state': 'no_photo', 'attendance_enroll_note': _('add a photo'),
                                  'attendance_enroll_checked': fields.Datetime.now()})
            else:
                people.append({'person_id': person.id, 'employee_id': person.employee_id.id,
                               'name': person.name, 'images': images})
        payload = {'people': people}
        version = cfg.version_of(payload)
        body = _body() or {}
        if body.get('have_version') == version:
            return _json({'changed': False, 'version': version})
        return _json({'changed': True, 'version': version, 'excluded': excluded, **payload})

    @http.route('/cctv/api/attendance/image/<string:kind>/<int:rec_id>', type='http', auth='public',
                methods=['GET'], csrf=False)
    def image(self, kind, rec_id, **kw):
        denied = self._guard()
        if denied:
            return denied
        env = request.env
        record, field, person = None, None, None
        if kind == 'person':
            record = env['cctv.person'].sudo().browse(rec_id).exists()
            field, person = 'photo', record
        elif kind == 'face':
            record = env['cctv.person.face.image'].sudo().browse(rec_id).exists()
            field, person = 'image', record.person_id
        elif kind == 'employee':
            record = env['hr.employee'].sudo().browse(rec_id).exists()
            field = 'image_1920'
            person = record.cctv_person_id if record else None
        if not record or not person or person._attendance_ineligible_reason() or not is_real_photo(record[field]):
            return _json({'error': 'not_found'}, 404)
        raw = base64.b64decode(record[field])
        mime = 'image/png' if raw[:8] == b'\x89PNG\r\n\x1a\n' else 'image/jpeg'
        return Response(raw, content_type=mime, headers=[('Cache-Control', 'private, max-age=3600')])

    @http.route('/cctv/api/attendance/punch', type='http', auth='public', methods=['POST'], csrf=False)
    def punch(self, **kw):
        denied = self._guard()
        if denied:
            return denied
        data = _body()
        if data is None:
            return _json({'error': 'bad_json'}, 400)
        env = request.env
        camera = env['cctv.camera'].sudo().search([('camera_code', '=', data.get('camera_code'))], limit=1)
        if not camera:
            return _json({'error': 'camera_not_found'}, 404)
        if not camera.ai_attendance:
            return _json({'error': 'not_an_attendance_camera'}, 409)
        when = _parse_time(data.get('event_time'))
        snapshot = data.get('snapshot_base64') or False
        FaceLog = env['cctv.face.log'].sudo().with_context(skip_attendance_hook=True)

        if data.get('unknown'):
            log = FaceLog.create({'camera_id': camera.id, 'is_unknown': True, 'snapshot': snapshot,
                                  'match_confidence': float(data.get('confidence') or 0),
                                  'detected_at': when or fields.Datetime.now()})
            if env['cctv.attendance.config'].param('alert_unknown'):
                env['cctv.alert'].sudo().create({
                    'name': 'Unknown Face Detected - %s' % camera.name, 'alert_type': 'unknown_face',
                    'camera_id': camera.id, 'office_id': camera.office_id.id, 'severity': 'medium'})
            return _json({'status': 'ok', 'face_log_id': log.id})

        try:
            person = env['cctv.person'].sudo().browse(int(data.get('person_id') or 0)).exists()
            confidence = float(data.get('confidence'))
        except (TypeError, ValueError):
            return _json({'error': 'bad_payload'}, 400)
        if not person:
            return _json({'error': 'person_not_found'}, 404)

        log = FaceLog.create({'camera_id': camera.id, 'person_id': person.id, 'is_unknown': False,
                              'match_confidence': confidence, 'snapshot': snapshot,
                              'detected_at': when or fields.Datetime.now()})
        person._note_sighting(camera)
        punch = env['cctv.attendance.punch'].register_sighting(
            camera, person, confidence, when=when, snapshot=snapshot, source='cctv_service',
            sightings=int(data.get('sightings') or 1), face_log=log)
        return _json({
            'status': 'ok', 'face_log_id': log.id, 'punch_id': punch.id or False,
            'result': punch.result if punch else 'no_action',
            'reason': punch.reason if punch else '',
            'employee': person.employee_id.name or person.name,
        })

    @http.route('/cctv/api/attendance/status', type='http', auth='public', methods=['POST'], csrf=False)
    def status(self, **kw):
        denied = self._guard()
        if denied:
            return denied
        data = _body() or {}
        env = request.env
        now = fields.Datetime.now()
        for code, info in (data.get('cameras') or {}).items():
            cam = env['cctv.camera'].sudo().search([('camera_code', '=', code)], limit=1)
            if not cam:
                continue
            state = (info or {}).get('state') or 'unknown'
            cam.write({'attendance_worker_status': state, 'attendance_worker_seen': now})
            if state == 'running':
                cam.action_mark_online()
        for item in data.get('gallery') or []:
            person = env['cctv.person'].sudo().browse(int(item.get('person_id') or 0)).exists()
            if person:
                person.write({'attendance_enroll_state': item.get('state') or 'unknown',
                              'attendance_enroll_note': (item.get('note') or '')[:250],
                              'attendance_enroll_checked': now})
        return _json({'status': 'ok'})
