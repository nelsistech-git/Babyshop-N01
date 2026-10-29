# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cctv_face')
class TestFaceAttendance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.office = cls.env['cctv.office'].create({'name': 'HQ'})
        Cam = cls.env['cctv.camera']
        mk = lambda name, direction: Cam.create({
            'name': name, 'office_id': cls.office.id, 'connection_type': 'rtsp',
            'rtsp_url': 'rtsp://127.0.0.1/%s' % name, 'ai_attendance': True, 'attendance_direction': direction})
        cls.cam_in, cls.cam_out, cls.cam_both = mk('door-in', 'in'), mk('door-out', 'out'), mk('door-both', 'both')
        cls.cam_plain = Cam.create({'name': 'plain', 'office_id': cls.office.id, 'rtsp_url': 'rtsp://127.0.0.1/p'})
        cls.emp = cls.env['hr.employee'].create({'name': 'Test Employee'})
        cls.emp.action_enroll_face()
        cls.person = cls.emp.cctv_person_id
        cls.Punch = cls.env['cctv.attendance.punch']
        cls.Att = cls.env['hr.attendance']

    def _punch(self, cam, conf=80.0, when=None, person=None):
        return self.Punch.register_sighting(cam, person or self.person, conf, when=when)

    def _ago(self, minutes):
        return fields.Datetime.now() - timedelta(minutes=minutes)

    def test_01_enrol_creates_employee_person(self):
        self.assertTrue(self.person)
        self.assertEqual(self.person.person_type, 'employee')
        self.assertEqual(self.person.employee_id, self.emp)

    def test_02_entry_camera_checks_in_once(self):
        p = self._punch(self.cam_in)
        self.assertEqual(p.result, 'check_in')
        att = p.attendance_id
        self.assertEqual(att.in_mode, 'cctv_face')
        self.assertEqual(att.cctv_in_camera_id, self.cam_in)
        self.assertFalse(att.check_out)
        self.assertFalse(self._punch(self.cam_in))       # already checked in -> nothing
        self.assertEqual(self.Att.search_count([('employee_id', '=', self.emp.id)]), 1)

    def test_03_exit_camera_checks_out_after_min_stay(self):
        self._punch(self.cam_in, when=self._ago(20))
        att = self.Att.search([('employee_id', '=', self.emp.id)])
        p = self._punch(self.cam_out)
        self.assertEqual(p.result, 'check_out')
        self.assertTrue(att.check_out)
        self.assertEqual(att.out_mode, 'cctv_face')
        self.assertEqual(att.cctv_out_camera_id, self.cam_out)

    def test_04_exit_camera_too_soon_is_ignored(self):
        self._punch(self.cam_in, when=self._ago(1))
        self.assertFalse(self._punch(self.cam_out))
        self.assertFalse(self.Att.search([('employee_id', '=', self.emp.id)]).check_out)

    def test_05_exit_without_checkin_is_ignored(self):
        self.assertFalse(self._punch(self.cam_out))
        self.assertEqual(self.Att.search_count([('employee_id', '=', self.emp.id)]), 0)

    def test_06_low_confidence_rejected_and_borderline_goes_to_review(self):
        self.assertFalse(self._punch(self.cam_in, conf=20))
        review = self._punch(self.cam_in, conf=50)
        self.assertEqual(review.result, 'review')
        self.assertEqual(self.Att.search_count([('employee_id', '=', self.emp.id)]), 0)
        self.assertTrue(self.env['cctv.alert'].search([('name', 'ilike', 'needs review')]))
        review.action_approve()
        self.assertEqual(review.result, 'check_in')
        self.assertEqual(review.attendance_id.in_mode, 'cctv_face')
        self.assertEqual(review.source, 'manual')

    def test_07_dismiss_review(self):
        review = self._punch(self.cam_in, conf=50)
        review.action_dismiss()
        self.assertEqual(review.result, 'dismissed')
        self.assertEqual(self.Att.search_count([('employee_id', '=', self.emp.id)]), 0)

    def test_08_single_door_toggles(self):
        p1 = self._punch(self.cam_both, when=self._ago(25))
        self.assertEqual(p1.result, 'check_in')
        self.assertFalse(self._punch(self.cam_both, when=self._ago(20)))   # 5 min gap < 10
        p2 = self._punch(self.cam_both)
        self.assertEqual(p2.result, 'check_out')

    def test_09_forgotten_checkout_is_closed_and_new_checkin_made(self):
        old_in = fields.Datetime.now() - timedelta(hours=30)
        old = self.Att.create({'employee_id': self.emp.id, 'check_in': old_in, 'in_mode': 'cctv_face'})
        p = self._punch(self.cam_in)
        self.assertEqual(p.result, 'check_in')
        self.assertTrue(old.check_out)
        self.assertTrue(old.cctv_auto_closed)
        self.assertLess(old.check_out, fields.Datetime.now() - timedelta(hours=10))   # never "now"
        self.assertNotEqual(p.attendance_id, old)

    def test_10_not_an_attendance_camera(self):
        self.assertFalse(self.Punch.register_sighting(self.cam_plain, self.person, 90.0))

    def test_11_attendance_can_be_switched_off_per_person(self):
        self.person.attendance_enabled = False
        self.assertFalse(self._punch(self.cam_in))

    def test_12_consent_required(self):
        self.env['ir.config_parameter'].sudo().set_param('cctv_management.attendance_require_consent', 'True')
        self.assertFalse(self._punch(self.cam_in))
        self.person.biometric_consent = True
        self.assertEqual(self._punch(self.cam_in).result, 'check_in')

    def test_13_old_punch_goes_to_review(self):
        p = self._punch(self.cam_in, when=self._ago(180))
        self.assertEqual(p.result, 'review')
        self.assertTrue(p.is_old)

    def test_14_visitor_is_never_punched(self):
        visitor = self.env['cctv.person'].create({'name': 'Visitor', 'person_type': 'visitor'})
        self.assertFalse(self.Punch.register_sighting(self.cam_in, visitor, 95.0))

    def test_15_late_minutes_from_monitor_assignment(self):
        import pytz
        self.emp.tz = 'UTC'
        now = fields.Datetime.now()
        start = now - timedelta(minutes=50)
        hour = start.hour + start.minute / 60.0
        if start.date() != now.date():
            self.skipTest('crosses midnight')
        self.env['cctv.employee.monitor'].create({
            'employee_id': self.emp.id, 'person_id': self.person.id, 'shift_start': hour,
            'shift_end': min(hour + 8, 23.9), 'grace_minutes': 15})
        p = self._punch(self.cam_in)
        self.assertGreater(p.attendance_id.cctv_late_minutes, 40)
        self.assertTrue(p.attendance_id.cctv_is_late)

    def test_16_event_api_hook_needs_several_frames(self):
        Log = self.env['cctv.face.log']
        vals = {'camera_id': self.cam_in.id, 'person_id': self.person.id, 'match_confidence': 85.0}
        Log.create(vals)
        Log.create(vals)
        self.assertEqual(self.Att.search_count([('employee_id', '=', self.emp.id)]), 0)
        Log.create(vals)
        self.assertEqual(self.Att.search_count([('employee_id', '=', self.emp.id)]), 1)

    def test_17_attendance_camera_needs_a_source(self):
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env['cctv.camera'].create({
                'name': 'nosrc', 'office_id': self.office.id, 'connection_type': 'ip', 'ip_address': '10.0.0.9',
                'brand': 'onvif_generic', 'ai_attendance': True})
