# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from datetime import timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import tagged

from .common import BondLicenseCommon


@tagged('post_install', '-at_install', 'bond_license')
class TestBondEntitlement(BondLicenseCommon):

    def setUp(self):
        super().setUp()
        self.lic = self._make_license()
        self.ent = self._make_entitlement(self.lic, amount=100.0)

    def test_initial_balances(self):
        self.assertEqual(self.ent.approved_total, 100.0)
        self.assertEqual(self.ent.used_amount, 0.0)
        self.assertEqual(self.ent.available_amount, 100.0)

    def test_utilization_reduces_balance(self):
        self._utilize(self.ent, self._make_done_move(30.0))
        self.assertEqual(self.ent.used_amount, 30.0)
        self.assertEqual(self.ent.available_amount, 70.0)

    def test_draft_utilization_not_counted(self):
        self._utilize(self.ent, self._make_done_move(30.0), validate=False)
        self.assertEqual(self.ent.used_amount, 0.0)

    def test_over_utilization_blocked(self):
        self._utilize(self.ent, self._make_done_move(80.0))
        with self.assertRaises(UserError):
            self._utilize(self.ent, self._make_done_move(30.0))
        self.assertEqual(self.ent.used_amount, 80.0)

    def test_authorized_exception_allows_over_utilization(self):
        with self.assertRaises(AccessError):
            self.ent.with_user(self.user_officer).write({
                'exception_authorized': True, 'exception_reference': 'R', 'exception_basis': 'B'})
        self.ent.with_user(self.user_manager).write({
            'exception_authorized': True, 'exception_reference': 'EXC-1', 'exception_basis': 'Test basis'})
        util = self._utilize(self.ent, self._make_done_move(120.0))
        self.assertTrue(util.exception_used)
        self.assertTrue(self.ent.over_utilized)
        self.assertEqual(self.ent.available_amount, -20.0)

    def test_exception_needs_reference(self):
        with self.assertRaises(ValidationError):
            self.ent.with_user(self.user_manager).write({'exception_authorized': True})

    def test_duplicate_utilization_blocked(self):
        move = self._make_done_move(10.0)
        self._utilize(self.ent, move)
        other = self._make_entitlement(self.lic, amount=100.0)
        with self.assertRaises(ValidationError):
            self._utilize(other, move, validate=False)

    def test_reversal_frees_balance_and_move(self):
        move = self._make_done_move(40.0)
        util = self._utilize(self.ent, move)
        self._manager_action(util, 'reverse', 'Wrong entitlement')
        self.assertEqual(util.state, 'reversed')
        self.assertEqual(self.ent.used_amount, 0.0)
        self._utilize(self.ent, move)
        self.assertEqual(self.ent.used_amount, 40.0)

    def test_product_mismatch_blocked(self):
        move = self._make_done_move(10.0, product=self.other_product)
        with self.assertRaises(UserError):
            self._utilize(self.ent, move)

    def test_license_not_valid_blocks(self):
        self._manager_action(self.lic, 'suspend')
        with self.assertRaises(UserError):
            self._utilize(self.ent, self._make_done_move(10.0))

    def test_unauthorized_location_blocked(self):
        other_loc = self.env['stock.location'].create({
            'name': 'Non Bonded', 'usage': 'internal',
            'location_id': self.warehouse.view_location_id.id})
        self.lic.write({'location_ids': [(6, 0, [other_loc.id])]})
        with self.assertRaises(UserError):
            self._utilize(self.ent, self._make_done_move(10.0))

    def test_move_outside_period_blocked(self):
        ent = self._make_entitlement(
            self.lic, period_from=self.today + timedelta(days=5),
            period_to=self.today + timedelta(days=50),
            effective_from=self.today + timedelta(days=5),
            effective_to=self.today + timedelta(days=50))
        with self.assertRaises(UserError):
            self._utilize(ent, self._make_done_move(10.0))

    def test_not_done_move_rejected(self):
        move = self._make_done_move(10.0)
        move.write({'state': 'assigned'})
        with self.assertRaises(UserError):
            self._utilize(self.ent, move)

    def test_value_basis(self):
        ent = self._make_entitlement(
            self.lic, amount=1000.0, basis='value', uom_id=False,
            currency_id=self.company.currency_id.id)
        self._utilize(ent, self._make_done_move(10.0, price=25.0))
        self.assertEqual(ent.used_amount, 250.0)
        self.assertEqual(ent.available_amount, 750.0)

    def test_balances_not_directly_editable(self):
        for fname in ('used_amount', 'available_amount', 'approved_total'):
            with self.assertRaises(UserError):
                self.ent.write({fname: 1.0})

    def test_original_values_locked(self):
        with self.assertRaises(UserError):
            self.ent.write({'original_amount': 999.0})
        with self.assertRaises(UserError):
            self.ent.write({'effective_to': self.today + timedelta(days=500)})

    def test_amendment_increases_total_and_keeps_original(self):
        amend = self.env['bond.warehouse.entitlement.amendment'].create({
            'entitlement_id': self.ent.id, 'approval_reference': 'AMD-1',
            'reason': 'Authority increased approval', 'change_amount': 50.0,
            'new_effective_to': self.today + timedelta(days=400)})
        self.assertEqual(self.ent.approved_total, 100.0)  # not effective until approved
        with self.assertRaises(AccessError):
            amend.with_user(self.user_officer).action_approve()
        amend.with_user(self.user_manager).action_approve()
        self.assertEqual(self.ent.original_amount, 100.0)
        self.assertEqual(self.ent.amended_total, 50.0)
        self.assertEqual(self.ent.approved_total, 150.0)
        self.assertEqual(self.ent.available_amount, 150.0)
        self.assertEqual(self.ent.original_effective_to, self.today + timedelta(days=300))
        self.assertEqual(self.ent.effective_to, self.today + timedelta(days=400))
        self.assertEqual((amend.previous_total, amend.new_total), (100.0, 150.0))
        with self.assertRaises(UserError):
            amend.write({'change_amount': 1.0})
        with self.assertRaises(UserError):
            amend.unlink()

    def test_amendment_cannot_go_below_used(self):
        self._utilize(self.ent, self._make_done_move(60.0))
        amend = self.env['bond.warehouse.entitlement.amendment'].create({
            'entitlement_id': self.ent.id, 'approval_reference': 'AMD-2',
            'reason': 'Reduction', 'change_amount': -50.0})
        with self.assertRaises(UserError):
            amend.with_user(self.user_manager).action_approve()

    def test_amendment_rejection(self):
        amend = self.env['bond.warehouse.entitlement.amendment'].create({
            'entitlement_id': self.ent.id, 'approval_reference': 'AMD-3',
            'reason': 'Request', 'change_amount': 10.0})
        self._manager_action(amend, 'reject', 'Not supported by authority letter')
        self.assertEqual(amend.state, 'rejected')
        self.assertEqual(self.ent.approved_total, 100.0)

    def test_empty_amendment_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['bond.warehouse.entitlement.amendment'].create({
                'entitlement_id': self.ent.id, 'approval_reference': 'X', 'reason': 'Y'})

    def test_entitlement_expiry_cron(self):
        self.env.cr.execute(
            "UPDATE bond_warehouse_entitlement SET effective_to = %s WHERE id = %s",
            (self.today - timedelta(days=1), self.ent.id))
        self.ent.invalidate_recordset()
        self.env['bond.warehouse.entitlement']._cron_check_expiry()
        self.assertEqual(self.ent.state, 'expired')

    def test_cancel_blocked_with_utilization(self):
        self._utilize(self.ent, self._make_done_move(10.0))
        with self.assertRaises(UserError):
            self._manager_action(self.ent, 'cancel')
        self._manager_action(self.ent, 'close')
        self.assertEqual(self.ent.state, 'closed')

    def test_activation_requires_license_and_data(self):
        ent = self._make_entitlement(self.lic, activate=False, hs_code=False)
        with self.assertRaises(UserError):
            ent.action_activate()

    def test_reader_cannot_validate(self):
        move = self._make_done_move(10.0)
        util = self._utilize(self.ent, move, validate=False)
        with self.assertRaises(AccessError):
            util.with_user(self.user_reader).action_validate()
