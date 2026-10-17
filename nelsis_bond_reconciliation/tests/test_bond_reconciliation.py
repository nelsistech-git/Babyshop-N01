# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'nelsis_bond')
class TestBondReconciliation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.wh = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        Loc = cls.env['stock.location']
        cls.bonded = Loc.create({'name': 'Bonded Store', 'location_id': cls.wh.lot_stock_id.id,
                                 'usage': 'internal', 'bond_scope': 'bonded'})
        cls.bonded_child = Loc.create({'name': 'Bonded Rack A', 'location_id': cls.bonded.id,
                                       'usage': 'internal'})
        cls.nonbonded = Loc.create({'name': 'Open Store', 'location_id': cls.wh.lot_stock_id.id,
                                    'usage': 'internal', 'bond_scope': 'non_bonded'})
        cls.supplier = cls.env.ref('stock.stock_location_suppliers')
        cls.customer = cls.env.ref('stock.stock_location_customers')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        cls.product = cls.env['product.product'].create({
            'name': 'Bond Leather', 'detailed_type': 'product', 'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id, 'bond_hs_code': '4107.00.00'})
        cls.manager = cls.env['res.users'].create({
            'name': 'Bond Manager', 'login': 'bond_mgr', 'email': 'bm@example.com',
            'groups_id': [Command.set([cls.env.ref('base.group_user').id,
                                       cls.env.ref('nelsis_bond_reconciliation.group_bond_recon_manager').id])]})
        cls.plain_user = cls.env['res.users'].create({
            'name': 'Bond User', 'login': 'bond_usr', 'email': 'bu@example.com',
            'groups_id': [Command.set([cls.env.ref('base.group_user').id,
                                       cls.env.ref('nelsis_bond_reconciliation.group_bond_recon_user').id])]})

    # ---------------------------------------------------------------- helpers
    def _move(self, product, qty, src, dst, uom=None, lc='LC-001', boe='BOE-001', lic='LIC-1', done=True):
        uom = uom or product.uom_id
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.wh.int_type_id.id,
            'location_id': src.id, 'location_dest_id': dst.id,
            'bond_lc_ref': lc, 'bond_boe_ref': boe, 'bond_license_ref': lic,
            'move_ids': [Command.create({
                'name': product.name, 'product_id': product.id, 'product_uom_qty': qty,
                'product_uom': uom.id, 'location_id': src.id, 'location_dest_id': dst.id})],
        })
        picking.action_confirm()
        if done:
            picking.move_ids.write({'quantity': qty, 'picked': True})
            picking.with_context(skip_backorder=True, skip_sms=True).button_validate()
        return picking

    def _recon(self, **kw):
        vals = {'date_from': fields.Date.today() - timedelta(days=60),
                'date_to': fields.Date.today() + timedelta(days=1),
                'bond_classification': 'bonded'}
        vals.update(kw)
        return self.env['bond.warehouse.reconciliation'].create(vals)

    def _line(self, recon, product=None):
        return recon.line_ids.filtered(lambda l: l.product_id == (product or self.product))

    def _quant_qty(self, product, locations):
        return sum(self.env['stock.quant'].search([
            ('product_id', '=', product.id), ('location_id', 'child_of', locations.ids)]).mapped('quantity'))

    # ------------------------------------------------------------------ tests
    def test_01_effective_classification_is_inherited(self):
        self.assertEqual(self.bonded_child.bond_scope_effective, 'bonded')

    def test_02_ledger_receipt_issue_running_balance(self):
        self._move(self.product, 100, self.supplier, self.bonded)
        self._move(self.product, 30, self.bonded, self.customer)
        rows = self.env['bond.warehouse.ledger'].search(
            [('product_id', '=', self.product.id), ('location_id', '=', self.bonded.id)], order='date, id')
        self.assertEqual(rows.mapped('move_type'), ['receipt', 'issue'])
        self.assertEqual(rows.mapped('running_balance'), [100.0, 70.0])

    def test_03_internal_transfer_has_no_company_effect(self):
        self._move(self.product, 50, self.supplier, self.bonded)
        self._move(self.product, 20, self.bonded, self.nonbonded)
        rows = self.env['bond.warehouse.ledger'].search(
            [('product_id', '=', self.product.id), ('move_type', '=', 'transfer')])
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(sum(rows.mapped('company_effect_qty')), 0.0)
        self.assertAlmostEqual(sum(rows.mapped('signed_qty')), 0.0)

    def test_04_closed_scope_ignores_internal_transfers(self):
        self._move(self.product, 50, self.supplier, self.bonded)
        self._move(self.product, 20, self.bonded, self.bonded_child)  # inside scope
        recon = self._recon()
        recon.action_compute()
        line = self._line(recon)
        self.assertEqual(line.receipt_qty, 50)
        self.assertEqual(line.transfer_in_qty, 0)
        self.assertEqual(line.transfer_out_qty, 0)
        self.assertEqual(line.closing_qty, 50)
        self.assertEqual(line.system_qty, 50)
        self.assertFalse(line.has_discrepancy)

    def test_05_boundary_transfer_to_non_bonded(self):
        self._move(self.product, 50, self.supplier, self.bonded)
        self._move(self.product, 20, self.bonded, self.nonbonded)
        recon = self._recon()
        recon.action_compute()
        line = self._line(recon)
        self.assertEqual(line.transfer_out_qty, 20)
        self.assertEqual(line.closing_qty, 30)
        self.assertEqual(line.system_qty, 30)

    def test_06_opening_balance_and_period(self):
        old = self._move(self.product, 40, self.supplier, self.bonded)
        old.move_line_ids.write({'date': fields.Datetime.now() - timedelta(days=40)})
        self._move(self.product, 10, self.supplier, self.bonded)
        recon = self._recon(date_from=fields.Date.today() - timedelta(days=5))
        recon.action_compute()
        line = self._line(recon)
        self.assertEqual(line.opening_qty, 40)
        self.assertEqual(line.receipt_qty, 10)
        self.assertEqual(line.closing_qty, 50)

    def test_07_multiple_uom_converted_to_product_uom(self):
        self._move(self.product, 2, self.supplier, self.bonded, uom=self.uom_dozen)
        recon = self._recon()
        recon.action_compute()
        self.assertEqual(self._line(recon).receipt_qty, 24)
        self.assertEqual(self._line(recon).closing_qty, 24)

    def test_08_draft_and_cancelled_transactions_excluded(self):
        self._move(self.product, 10, self.supplier, self.bonded)
        self._move(self.product, 99, self.supplier, self.bonded, done=False)
        cancelled = self._move(self.product, 77, self.supplier, self.bonded, done=False)
        cancelled.action_cancel()
        recon = self._recon()
        recon.action_compute()
        self.assertEqual(self._line(recon).receipt_qty, 10)

    def test_09_physical_discrepancy_workflow(self):
        self._move(self.product, 10, self.supplier, self.bonded)
        recon = self._recon()
        recon.action_compute()
        self.assertEqual(recon.state, 'in_progress')
        line = self._line(recon)
        line.write({'physical_counted': True, 'physical_qty': 8})
        self.assertTrue(line.has_discrepancy)
        self.assertEqual(line.physical_diff, -2)
        recon.action_refresh_state()
        self.assertEqual(recon.state, 'discrepancy')
        with self.assertRaises(UserError):
            recon.action_submit_review()
        line.write({'reason': 'Two rolls damaged'})
        recon.action_submit_review()
        self.assertEqual(recon.state, 'review')

    def test_10_adjustment_requires_approval(self):
        self._move(self.product, 10, self.supplier, self.bonded)
        quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id, 'location_id': self.bonded.id, 'inventory_quantity': 15})
        quant.action_apply_inventory()
        recon = self._recon()
        recon.action_compute()
        line = self._line(recon)
        self.assertEqual(line.adjustment_qty, 0)
        self.assertEqual(line.unapproved_adjustment_qty, 5)
        self.assertEqual(line.system_diff, 5)
        self.assertTrue(line.has_discrepancy)
        adj = self.env['stock.move.line'].search([
            ('product_id', '=', self.product.id), ('move_id.is_inventory', '=', True)])
        with self.assertRaises(UserError):
            adj.with_user(self.plain_user).action_bond_approve_adjustment()
        adj.with_user(self.manager).action_bond_approve_adjustment()
        recon.action_compute()
        line = self._line(recon)
        self.assertEqual(line.adjustment_qty, 5)
        self.assertEqual(line.closing_qty, 15)
        self.assertFalse(line.has_discrepancy)

    def test_11_approval_segregation_and_reopen(self):
        self._move(self.product, 10, self.supplier, self.bonded)
        recon = self._recon()
        recon.action_compute()
        recon.action_submit_review()
        recon.action_request_approval()
        self.assertEqual(recon.state, 'approval')
        with self.assertRaises(UserError):
            recon.with_user(self.plain_user).action_approve()
        # preparer (current user) is not allowed to approve own record
        recon.prepared_by_id = self.plain_user
        recon.with_user(self.manager).action_approve()
        self.assertEqual(recon.state, 'reconciled')
        recon.with_user(self.manager).action_close()
        self.assertEqual(recon.state, 'closed')
        with self.assertRaises(UserError):
            recon.with_user(self.plain_user).action_open_reopen_wizard()
        wizard = self.env['bond.reconciliation.reopen.wizard'].with_user(self.manager).create({
            'reconciliation_id': recon.id, 'reason': 'Late customs correction'})
        wizard.action_confirm()
        self.assertEqual(recon.state, 'in_progress')
        self.assertEqual(len(recon.reopen_ids), 1)

    def test_12_locked_after_review_and_no_delete(self):
        self._move(self.product, 10, self.supplier, self.bonded)
        recon = self._recon()
        recon.action_compute()
        recon.action_submit_review()
        with self.assertRaises(UserError):
            self._line(recon).write({'physical_qty': 3})
        with self.assertRaises(UserError):
            recon.unlink()
        with self.assertRaises(UserError):
            recon.write({'date_to': fields.Date.today()})

    def test_13_register_matches_standard_inventory(self):
        self._move(self.product, 60, self.supplier, self.bonded, lc='LC-A', boe='BOE-A')
        self._move(self.product, 15, self.bonded, self.customer, lc='LC-A', boe='BOE-A')
        register = self.env['bond.warehouse.register'].search([
            ('product_id', '=', self.product.id), ('location_id', '=', self.bonded.id)])
        self.assertEqual(sum(register.mapped('balance_qty')), self._quant_qty(self.product, self.bonded))
        self.assertEqual(sum(register.mapped('received_qty')), 60)
        self.assertEqual(sum(register.mapped('issued_qty')), 15)
        self.assertEqual(register.lc_ref, 'LC-A')
        self.assertEqual(register.traceable_balance_qty, 45)

    def test_14_lc_filter_disables_system_comparison(self):
        self._move(self.product, 10, self.supplier, self.bonded, lc='LC-X')
        self._move(self.product, 5, self.supplier, self.bonded, lc='LC-Y')
        recon = self._recon(lc_ref='LC-X')
        recon.action_compute()
        line = self._line(recon)
        self.assertEqual(line.closing_qty, 10)
        self.assertFalse(recon.system_check_applicable)
        self.assertFalse(line.has_discrepancy)

    def test_15_reports_run_and_csv_exports(self):
        self._move(self.product, 10, self.supplier, self.bonded)
        recon = self._recon()
        recon.action_compute()
        wizard_model = self.env['bond.warehouse.report.wizard']
        types = [t[0] for t in wizard_model._fields['report_type'].selection]
        self.assertEqual(len(types), 12)
        for rtype in types:
            wiz = wizard_model.create({
                'report_type': rtype, 'date_from': fields.Date.today() - timedelta(days=30),
                'date_to': fields.Date.today() + timedelta(days=1), 'bond_classification': 'all'})
            data = wiz._get_report_data()
            self.assertIn('INTERNAL MANAGEMENT REPORT', data['notice'], rtype)
            self.assertEqual(len(data['headers']) > 0, True, rtype)
            action = wiz.action_export_csv()
            self.assertEqual(action['type'], 'ir.actions.act_url')

    def test_16_rir_report_ties_to_inventory(self):
        self._move(self.product, 30, self.supplier, self.bonded)
        self._move(self.product, 10, self.bonded, self.customer)
        wiz = self.env['bond.warehouse.report.wizard'].create({
            'report_type': 'rir', 'bond_classification': 'bonded',
            'date_from': fields.Date.today() - timedelta(days=1),
            'date_to': fields.Date.today() + timedelta(days=1)})
        data = wiz._get_report_data()
        row = next(r for r in data['rows'] if 'Bond Leather' in str(r[0]))
        self.assertEqual(row[-1], self._quant_qty(self.product, self.bonded))

    def test_17_bond_refs_locked_on_done_picking(self):
        picking = self._move(self.product, 5, self.supplier, self.bonded)
        with self.assertRaises(UserError):
            picking.with_user(self.plain_user).write({'bond_lc_ref': 'CHANGED'})
        picking.with_user(self.manager).write({'bond_lc_ref': 'CHANGED'})
        self.assertEqual(picking.bond_lc_ref, 'CHANGED')
