# -*- coding: utf-8 -*-
import base64
import io
import json

from PIL import Image

from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install', 'cctv_face')
class TestAttendanceApi(HttpCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param('cctv_management.api_key', 'secret-key')
        office = self.env['cctv.office'].create({'name': 'HQ API'})
        self.cam = self.env['cctv.camera'].create({
            'name': 'api-door', 'office_id': office.id, 'rtsp_url': 'rtsp://127.0.0.1/x',
            'ai_attendance': True, 'attendance_direction': 'in'})
        self.emp = self.env['hr.employee'].create({'name': 'Api Employee', 'image_1920': self._png()})
        self.emp.action_enroll_face()
        self.person = self.emp.cctv_person_id

    @staticmethod
    def _png():
        buf = io.BytesIO()
        Image.new('RGB', (64, 64), (200, 150, 120)).save(buf, 'PNG')
        return base64.b64encode(buf.getvalue())

    def _post(self, path, data=None, key='secret-key'):
        return self.url_open(path, data=json.dumps(data or {}), headers={
            'Content-Type': 'application/json', 'X-CCTV-API-KEY': key})

    def test_requires_api_key(self):
        self.assertEqual(self._post('/cctv/api/attendance/config', key='wrong').status_code, 401)

    def test_config_lists_attendance_cameras(self):
        res = self._post('/cctv/api/attendance/config').json()
        codes = [c['camera_code'] for c in res['cameras']]
        self.assertIn(self.cam.camera_code, codes)
        again = self._post('/cctv/api/attendance/config', {'have_version': res['version']}).json()
        self.assertFalse(again['changed'])

    def test_gallery_and_image(self):
        res = self._post('/cctv/api/attendance/gallery').json()
        mine = [p for p in res['people'] if p['person_id'] == self.person.id]
        self.assertEqual(len(mine), 1)
        img = mine[0]['images'][0]
        r = self.url_open('/cctv/api/attendance/image/%s/%s' % (img['kind'], img['id']),
                          headers={'X-CCTV-API-KEY': 'secret-key'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'\x89PNG'))
        self.assertEqual(self.url_open('/cctv/api/attendance/image/%s/%s' % (img['kind'], img['id'])).status_code, 401)

    def test_punch_creates_attendance(self):
        res = self._post('/cctv/api/attendance/punch', {
            'camera_code': self.cam.camera_code, 'person_id': self.person.id, 'confidence': 82.5,
            'sightings': 3}).json()
        self.assertEqual(res['result'], 'check_in')
        att = self.env['hr.attendance'].search([('employee_id', '=', self.emp.id)])
        self.assertEqual(len(att), 1)
        self.assertEqual(att.in_mode, 'cctv_face')
        again = self._post('/cctv/api/attendance/punch', {
            'camera_code': self.cam.camera_code, 'person_id': self.person.id, 'confidence': 82.5}).json()
        self.assertEqual(again['result'], 'no_action')

    def test_unknown_face_is_logged_not_punched(self):
        res = self._post('/cctv/api/attendance/punch', {
            'camera_code': self.cam.camera_code, 'unknown': True, 'confidence': 12}).json()
        self.assertEqual(res['status'], 'ok')
        self.assertTrue(self.env['cctv.face.log'].browse(res['face_log_id']).is_unknown)

    def test_status_updates_camera_and_enrolment(self):
        self._post('/cctv/api/attendance/status', {
            'cameras': {self.cam.camera_code: {'state': 'running'}},
            'gallery': [{'person_id': self.person.id, 'state': 'no_face', 'note': 'x'}]})
        self.env.invalidate_all()
        self.assertEqual(self.cam.attendance_state, 'running')
        self.assertEqual(self.person.attendance_enroll_state, 'no_face')

    def test_person_without_photo_is_flagged(self):
        emp = self.env['hr.employee'].create({'name': 'No Photo Employee'})
        emp.action_enroll_face()
        res = self._post('/cctv/api/attendance/gallery').json()
        self.assertNotIn(emp.cctv_person_id.id, [p['person_id'] for p in res['people']])
        self.env.invalidate_all()
        self.assertEqual(emp.cctv_person_id.attendance_enroll_state, 'no_photo')
