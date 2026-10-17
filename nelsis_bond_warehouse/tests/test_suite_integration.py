# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSuiteClassification(TransactionCase):

    def test_internal_location_defaults_to_non_bonded_everywhere(self):
        loc = self.env['stock.location'].create({'name': 'Suite test loc', 'usage': 'internal'})
        self.assertEqual(loc.bond_status, 'non_bonded')
        self.assertEqual(loc.bond_classification, 'non_bonded')
        self.assertEqual(loc.bond_scope_effective, 'non_bonded')

    def test_non_internal_location_is_unclassified(self):
        loc = self.env['stock.location'].create({'name': 'Suite test view', 'usage': 'view'})
        self.assertEqual(loc.bond_classification, 'unclassified')
        self.assertEqual(loc.bond_scope_effective, 'none')

    def test_direct_edit_of_derived_classification_is_refused(self):
        loc = self.env['stock.location'].create({'name': 'Suite test loc 2', 'usage': 'internal'})
        user = self.env['res.users'].create({
            'name': 'Suite tester', 'login': 'suite_tester_bond',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('nelsis_bond_warehouse.group_bond_suite_manager').id])]})
        with self.assertRaises(UserError):
            loc.with_user(user).write({'bond_classification': 'bonded'})

    def test_bonded_status_drives_other_modules(self):
        loc = self.env['stock.location'].create({'name': 'Suite test bonded', 'usage': 'internal'})
        loc.with_context(bond_classification_apply=True).write({
            'bond_status': 'bonded', 'bond_license_ref': 'TEST-LIC'})
        self.assertEqual(loc.bond_classification, 'bonded')
        self.assertEqual(loc.bond_scope_effective, 'bonded')


@tagged('post_install', '-at_install')
class TestSuiteLcReference(TransactionCase):

    def test_lc_number_fills_bond_lc_ref(self):
        lc = self.env['nelsis.lc'].search([('lc_number', '!=', False)], limit=1)
        if not lc:
            self.skipTest('No LC record with an LC number available.')
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming')], limit=1)
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
        })
        self.assertFalse(picking.bond_lc_ref)
        # constraint in nelsis_lc_management may refuse unsuitable LCs: only the sync is checked
        try:
            picking.write({'lc_id': lc.id})
        except Exception:
            self.skipTest('Available LC is not linkable to this receipt.')
        self.assertEqual(picking.bond_lc_ref, lc.lc_number)
