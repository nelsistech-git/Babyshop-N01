# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase, tagged

from ..utils import attendance_policy as P

T = datetime(2026, 10, 26, 9, 0)


@tagged('post_install', '-at_install', 'cctv_face')
class TestPolicy(TransactionCase):

    def test_entry_camera_only_checks_in(self):
        self.assertEqual(P.decide('in', False, None, None, T)[0], P.CHECK_IN)
        self.assertEqual(P.decide('in', True, T, T, T + timedelta(hours=2))[0], P.IGNORE)

    def test_exit_camera_only_checks_out(self):
        self.assertEqual(P.decide('out', False, None, None, T)[0], P.IGNORE)
        self.assertEqual(P.decide('out', True, T, T, T + timedelta(minutes=2))[0], P.IGNORE)
        self.assertEqual(P.decide('out', True, T, T, T + timedelta(hours=9))[0], P.CHECK_OUT)

    def test_single_door_toggles_with_gap(self):
        self.assertEqual(P.decide('both', True, T, T, T + timedelta(minutes=3))[0], P.IGNORE)
        self.assertEqual(P.decide('both', True, T, T, T + timedelta(minutes=30))[0], P.CHECK_OUT)
        self.assertEqual(P.decide('both', False, None, T, T + timedelta(minutes=30))[0], P.CHECK_IN)

    def test_never_rewrites_history(self):
        self.assertEqual(P.decide('in', False, None, T, T - timedelta(minutes=5))[0], P.IGNORE)

    def test_stale_open_attendance(self):
        old = T - timedelta(hours=30)
        self.assertEqual(P.decide('in', True, old, old, T)[0], P.CLOSE_STALE_AND_CHECK_IN)
        self.assertEqual(P.decide('out', True, old, old, T)[0], P.IGNORE)

    def test_confidence_bands(self):
        self.assertEqual(P.classify_confidence(60, 55, 45), P.ACCEPT)
        self.assertEqual(P.classify_confidence(50, 55, 45), P.REVIEW)
        self.assertEqual(P.classify_confidence(30, 55, 45), P.REJECT)
        self.assertEqual(P.classify_confidence(None, 55, 45), P.REJECT)

    def test_normalize_time(self):
        now = T
        self.assertEqual(P.normalize_time(None, now), (now, False))
        self.assertEqual(P.normalize_time(now + timedelta(hours=1), now), (now, False))
        old = now - timedelta(hours=2)
        self.assertEqual(P.normalize_time(old, now), (old, True))
