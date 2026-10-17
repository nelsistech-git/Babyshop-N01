# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from datetime import timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .common import BondLicenseCommon


@tagged('post_install', '-at_install', 'bond_license')
class TestBondSecurity(BondLicenseCommon):

    def test_activation_requires_values(self):
        lic = self._make_license()
        sec = self.env['bond.warehouse.security'].create({'license_id': lic.id})
        with self.assertRaises(UserError):
            sec.action_activate()

    def test_negative_amount_rejected(self):
        lic = self._make_license()
        with self.assertRaises(ValidationError):
            self._make_security(lic, activate=False, amount=-5)

    def test_security_expiry_cron(self):
        lic = self._make_license()
        sec = self._make_security(lic)
        self.env.cr.execute(
            "UPDATE bond_warehouse_security SET expiry_date = %s WHERE id = %s",
            (self.today - timedelta(days=1), sec.id))
        sec.invalidate_recordset()
        self.env['bond.warehouse.security']._cron_check_expiry()
        self.assertEqual(sec.state, 'expired')

    def test_locked_after_activation(self):
        lic = self._make_license()
        sec = self._make_security(lic)
        with self.assertRaises(UserError):
            sec.write({'amount': 5000.0})

    def test_renewal_replaces_previous(self):
        lic = self._make_license()
        sec = self._make_security(lic)
        action = sec.action_renew()
        new = self.env['bond.warehouse.security'].browse(action['res_id'])
        self.assertEqual(new.renewed_from_id, sec)
        self.assertEqual(new.state, 'draft')
        new.write({'instrument_number': 'INS-RENEWED',
                   'issue_date': self.today, 'expiry_date': self.today + timedelta(days=400)})
        new.action_activate()
        self.assertEqual(new.state, 'active')
        self.assertEqual(sec.state, 'renewed')
        self.assertIn(new, sec.renewed_by_ids)

    def test_release(self):
        lic = self._make_license()
        sec = self._make_security(lic)
        self._manager_action(sec, 'release', 'Released by authority ref X')
        self.assertEqual(sec.state, 'released')
        with self.assertRaises(UserError):
            sec.unlink()
