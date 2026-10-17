# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from datetime import timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import tagged

from .common import BondLicenseCommon


@tagged('post_install', '-at_install', 'bond_license')
class TestBondLicense(BondLicenseCommon):

    def test_validity_window(self):
        lic = self._make_license()
        self.assertEqual(lic.state, 'active')
        self.assertTrue(lic._is_valid_on(self.today))
        self.assertFalse(lic._is_valid_on(lic.effective_date - timedelta(days=1)))
        self.assertFalse(lic._is_valid_on(lic.expiry_date + timedelta(days=1)))

    def test_date_constraint(self):
        with self.assertRaises(ValidationError):
            self._make_license(activate=False, effective_date=self.today,
                               expiry_date=self.today - timedelta(days=1))

    def test_cannot_activate_expired(self):
        lic = self._make_license(activate=False, expiry_date=self.today - timedelta(days=1))
        with self.assertRaises(UserError):
            lic.action_activate()

    def test_rule_verification_gate(self):
        self.company.bond_require_verified_rule = True
        lic = self._make_license(activate=False)
        with self.assertRaises(UserError):
            lic.action_activate()
        with self.assertRaises(AccessError):
            lic.with_user(self.user_officer).action_verify_rule()
        lic.write({'rule_reference': 'TEST-RULE', 'rule_source_url': 'https://example.invalid',
                   'rule_applicability': 'Test applicability'})
        lic.with_user(self.user_manager).action_verify_rule()
        self.assertEqual(lic.rule_verification_status, 'verified')
        lic.action_activate()
        self.assertEqual(lic.state, 'active')
        # editing the rule content resets verification
        lic.write({'rule_reference': 'CHANGED'})
        self.assertEqual(lic.rule_verification_status, 'unverified')

    def test_expiry_cron(self):
        lic = self._make_license(activate=False, effective_date=self.today - timedelta(days=60),
                                 issue_date=self.today - timedelta(days=60),
                                 expiry_date=self.today + timedelta(days=1))
        lic.action_activate()
        lic.with_context(bond_renewal=True).write({'expiry_date': self.today - timedelta(days=1)})
        self.env['bond.warehouse.license']._cron_check_expiry()
        self.assertEqual(lic.state, 'expired')
        self.assertTrue(lic.history_ids.filtered(lambda h: h.event == 'expired'))

    def test_renewal_flow_reactivates_expired(self):
        lic = self._make_license()
        lic.with_context(bond_renewal=True).write({'expiry_date': self.today - timedelta(days=1)})
        lic._bond_mark_expired()
        old_expiry = lic.expiry_date
        renewal = self.env['bond.warehouse.license.renewal'].create({
            'license_id': lic.id, 'application_reference': 'APPL-1',
            'requested_expiry_date': self.today + timedelta(days=365)})
        renewal.action_submit()
        self.assertEqual(renewal.previous_expiry_date, old_expiry)
        with self.assertRaises(AccessError):
            renewal.with_user(self.user_officer).action_approve()
        renewal.approval_reference = 'APPR-1'
        renewal.with_user(self.user_manager).action_approve()
        self.assertEqual(lic.state, 'active')
        self.assertEqual(lic.expiry_date, self.today + timedelta(days=365))
        self.assertEqual(renewal.state, 'approved')

    def test_single_open_renewal(self):
        lic = self._make_license()
        vals = {'license_id': lic.id, 'requested_expiry_date': self.today + timedelta(days=400)}
        self.env['bond.warehouse.license.renewal'].create(vals)
        with self.assertRaises(ValidationError):
            self.env['bond.warehouse.license.renewal'].create(vals)

    def test_renewal_must_extend(self):
        lic = self._make_license()
        renewal = self.env['bond.warehouse.license.renewal'].create({
            'license_id': lic.id, 'application_reference': 'A',
            'requested_expiry_date': lic.expiry_date})
        with self.assertRaises(UserError):
            renewal.action_submit()

    def test_expiry_locked_outside_renewal(self):
        lic = self._make_license()
        with self.assertRaises(UserError):
            lic.write({'expiry_date': self.today + timedelta(days=999)})
        with self.assertRaises(UserError):
            lic.write({'license_number': 'CHANGED'})

    def test_suspend_and_reinstate(self):
        lic = self._make_license()
        self._manager_action(lic, 'suspend')
        self.assertEqual(lic.state, 'suspended')
        self.assertFalse(lic._is_valid_on(self.today))
        self._manager_action(lic, 'reinstate')
        self.assertEqual(lic.state, 'active')
        self.assertGreaterEqual(len(lic.history_ids), 4)

    def test_cancel_and_delete_protection(self):
        lic = self._make_license()
        with self.assertRaises(UserError):
            lic.unlink()
        self._manager_action(lic, 'cancel')
        self.assertEqual(lic.state, 'cancelled')
        draft = self._make_license(activate=False)
        draft.unlink()

    def test_reminders_scheduled_once(self):
        lic = self._make_license(activate=False, expiry_date=self.today + timedelta(days=10))
        lic.action_activate()
        Model = self.env['bond.warehouse.license']
        Model._cron_send_expiry_reminders()
        count = len(lic.activity_ids)
        self.assertEqual(count, 1)
        self.assertEqual(lic.last_reminder_days, 15)
        Model._cron_send_expiry_reminders()
        self.assertEqual(len(lic.activity_ids), count)

    def test_access_control(self):
        lic = self._make_license()
        with self.assertRaises(AccessError):
            lic.with_user(self.user_reader).write({'note': 'x'})
        with self.assertRaises(AccessError):
            self.env['bond.warehouse.license'].with_user(self.user_reader).create(self._license_vals())
        lic.with_user(self.user_officer).write({'note': 'ok'})
        wiz = self.env['bond.warehouse.status.wizard'].with_user(self.user_officer).create({
            'res_model': lic._name, 'res_id': lic.id, 'action_code': 'suspend', 'reason': 'x'})
        with self.assertRaises(AccessError):
            wiz.action_confirm()

    def test_audit_trail_immutable(self):
        lic = self._make_license()
        with self.assertRaises(UserError):
            lic.history_ids[:1].write({'note': 'tamper'})
        with self.assertRaises(UserError):
            lic.history_ids[:1].unlink()
