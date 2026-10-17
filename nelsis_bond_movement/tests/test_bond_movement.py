# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed
import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'nelsis_bond_movement')
class TestBondMovement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.Movement = cls.env['bond.warehouse.movement']

        def make_user(login, xmlid):
            return cls.env['res.users'].with_context(no_reset_password=True).create({
                'name': login, 'login': login, 'email': '%s@example.com' % login,
                'company_id': cls.company.id, 'company_ids': [(6, 0, [cls.company.id])],
                'groups_id': [(6, 0, [cls.env.ref(xmlid).id])],
            })
        cls.preparer = make_user('bond_preparer', 'nelsis_bond_movement.group_bond_movement_user')
        cls.approver = make_user('bond_approver', 'nelsis_bond_movement.group_bond_movement_manager')
        cls.controller = make_user('bond_controller', 'nelsis_bond_movement.group_bond_movement_controller')

        wh = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)

        def make_loc(name, classification):
            return cls.env['stock.location'].create({
                'name': name, 'usage': 'internal', 'location_id': wh.view_location_id.id,
                'company_id': cls.company.id, 'bond_classification': classification,
                'bond_movement_allowed': True})
        cls.loc_a = make_loc('BOND-A', 'bonded')
        cls.loc_b = make_loc('BOND-B', 'bonded')
        cls.loc_nb = make_loc('NONBOND-1', 'non_bonded')
        cls.consumption = cls.env.ref('nelsis_bond_movement.location_bond_consumption')

        cls.product = cls.env['product.product'].create({
            'name': 'Test Leather', 'detailed_type': 'product', 'tracking': 'lot'})
        cls.lot = cls.env['stock.lot'].create({
            'name': 'LOT-001', 'product_id': cls.product.id, 'company_id': cls.company.id})
        # Test fixture only: seed opening stock through the standard quant API.
        cls.env['stock.quant']._update_available_quantity(cls.product, cls.loc_a, 100.0, lot_id=cls.lot)
        cls.attachment = cls.env['ir.attachment'].create({
            'name': 'count.txt', 'datas': base64.b64encode(b'count sheet')})

    # ------------------------------------------------------------------ helpers
    def _qty(self, loc):
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id), ('location_id', '=', loc.id),
            ('lot_id', '=', self.lot.id)])
        return sum(quants.mapped('quantity'))

    def _company_total(self):
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product.id), ('location_id.usage', '=', 'internal'),
            ('company_id', '=', self.company.id)])
        return sum(quants.mapped('quantity'))

    def _new(self, mtype, **kw):
        vals = {'movement_type': mtype, 'product_id': self.product.id, 'lot_id': self.lot.id,
                'bond_classification': 'bonded', 'license_ref': 'LIC-TEST', 'reason': 'Test'}
        vals.update(kw)
        return self.Movement.with_user(self.preparer).create(vals)

    def _post(self, mov, approver=None):
        approver = approver or self.approver
        mov.with_user(self.preparer).action_submit()
        mov.with_user(approver).action_approve()
        mov.with_user(approver).action_validate()
        return mov

    def _transfer(self, qty=30.0, **kw):
        return self._new('transfer', quantity=qty, location_id=self.loc_a.id,
                         location_dest_id=self.loc_b.id, **kw)

    def _issue(self, qty=40.0):
        return self._new('issue', quantity=qty, location_id=self.loc_a.id,
                         operational_ref='JOB-1', recipient_ref='Cutting', support_approval_ref='REQ-1')

    def _return(self, issue, qty, **kw):
        vals = dict(origin_issue_id=issue.id, quantity=qty, location_id=self.consumption.id,
                    location_dest_id=self.loc_a.id, return_condition='good', inspection_result='OK')
        vals.update(kw)
        return self._new('return', **vals)

    # ------------------------------------------------------------------ tests
    def test_internal_transfer_nets_to_zero(self):
        total_before = self._company_total()
        mov = self._post(self._transfer(30.0))
        self.assertEqual(mov.state, 'done')
        self.assertEqual(self._qty(self.loc_a), 70.0)
        self.assertEqual(self._qty(self.loc_b), 30.0)
        self.assertEqual(self._company_total(), total_before, "Transfers must net to zero company-wide")
        self.assertEqual(mov.move_id.bond_movement_id, mov)
        self.assertTrue(mov.approved_by_id and mov.validation_date)

    def test_issue_validation(self):
        mov = self._post(self._issue(40.0))
        self.assertEqual(mov.state, 'done')
        self.assertEqual(mov.location_dest_id, self.consumption)
        self.assertEqual(self._qty(self.loc_a), 60.0)

    def test_insufficient_stock(self):
        mov = self._issue(500.0)
        mov.with_user(self.preparer).action_submit()
        mov.with_user(self.approver).action_approve()
        with self.assertRaises(UserError):
            mov.with_user(self.approver).action_validate()
        self.assertEqual(mov.state, 'approved')
        self.assertFalse(mov.move_id)
        self.assertEqual(self._qty(self.loc_a), 100.0)

    def test_partial_return_and_excessive_return(self):
        issue = self._post(self._issue(40.0))
        self._post(self._return(issue, 10.0))
        self.assertEqual(issue.returned_qty, 10.0)
        self.assertEqual(issue.outstanding_qty, 30.0)
        self.assertEqual(self._qty(self.loc_a), 70.0)
        # excessive return is blocked
        excessive = self._return(issue, 50.0)
        with self.assertRaises(UserError):
            excessive.with_user(self.preparer).action_submit()
        # documented, authorized exception allows it
        excessive.with_user(self.preparer).write({'exception_note': 'Supplier credit note CN-77'})
        with self.assertRaises(AccessError):
            excessive.with_user(self.approver).action_grant_exception()
        excessive.with_user(self.controller).action_grant_exception()
        self._post(excessive)
        self.assertEqual(excessive.state, 'done')

    def test_unapproved_adjustment(self):
        adj = self._new('adjustment', location_id=self.loc_a.id, count_ref='CNT-1', counted_qty=90.0,
                        evidence_ids=[(6, 0, [self.attachment.id])])
        with self.assertRaises(AccessError):
            adj.with_user(self.preparer).action_validate()
        adj.with_user(self.preparer).action_submit()
        self.assertEqual(adj.system_qty, 100.0)
        self.assertEqual(adj.variance, -10.0)
        with self.assertRaises(UserError):  # submitted but not approved
            adj.with_user(self.approver).action_validate()
        with self.assertRaises(AccessError):  # preparer cannot approve
            adj.with_user(self.preparer).action_approve()
        self.assertEqual(self._qty(self.loc_a), 100.0)
        adj.with_user(self.approver).action_approve()
        adj.with_user(self.approver).action_validate()
        self.assertEqual(self._qty(self.loc_a), 90.0)

    def test_adjustment_needs_evidence(self):
        adj = self._new('adjustment', location_id=self.loc_a.id, count_ref='CNT-2', counted_qty=95.0)
        with self.assertRaises(UserError):
            adj.with_user(self.preparer).action_submit()

    def test_duplicate_posting_blocked(self):
        mov = self._post(self._transfer(30.0))
        with self.assertRaises(UserError):
            mov.with_user(self.approver).action_validate()
        self.assertEqual(self._qty(self.loc_a), 70.0)
        self.assertEqual(self._qty(self.loc_b), 30.0)
        self.assertEqual(self.env['stock.move'].search_count([('bond_movement_id', '=', mov.id)]), 1)

    def test_reversal_requires_reason_and_restores_stock(self):
        mov = self._post(self._transfer(30.0))
        with self.assertRaises(UserError):
            mov.with_user(self.approver).action_reverse('')
        mov.with_user(self.approver).action_reverse('Wrong location')
        self.assertEqual(mov.state, 'reversed')
        self.assertTrue(mov.reversal_move_id and mov.reversal_reason)
        self.assertEqual(self._qty(self.loc_a), 100.0)
        self.assertEqual(self._qty(self.loc_b), 0.0)
        with self.assertRaises(UserError):
            mov.with_user(self.approver).action_reverse('Again')

    def test_issue_with_returns_cannot_be_reversed(self):
        issue = self._post(self._issue(40.0))
        self._post(self._return(issue, 10.0))
        with self.assertRaises(UserError):
            issue.with_user(self.approver).action_reverse('Mistake')

    def test_reclassification_needs_controller(self):
        mov = self._new('transfer', quantity=10.0, location_id=self.loc_a.id,
                        location_dest_id=self.loc_nb.id)
        with self.assertRaises(UserError):  # no justification
            mov.with_user(self.preparer).action_submit()
        mov.with_user(self.preparer).write({'reclass_reason': 'Duty paid release, BoE-123'})
        mov.with_user(self.preparer).action_submit()
        with self.assertRaises(AccessError):
            mov.with_user(self.approver).action_approve()
        self._post_after_submit(mov)
        self.assertEqual(self._qty(self.loc_nb), 10.0)

    def _post_after_submit(self, mov):
        mov.with_user(self.controller).action_approve()
        mov.with_user(self.controller).action_validate()

    def test_location_reclassification_protected(self):
        with self.assertRaises(AccessError):
            self.loc_a.with_user(self.approver).write({'bond_classification': 'non_bonded'})
        with self.assertRaises(UserError):  # stock exists, even for superuser
            self.loc_a.write({'bond_classification': 'non_bonded'})

    def test_audit_protection(self):
        mov = self._post(self._transfer(30.0))
        with self.assertRaises(UserError):
            mov.with_user(self.approver).write({'quantity': 1.0})
        with self.assertRaises(UserError):
            mov.with_user(self.approver).unlink()
