# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged('post_install', '-at_install')
class TestNelsisLc(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        today = fields.Date.today()
        cls.today = today
        cls.supplier = cls.env['res.partner'].create({'name': 'Test Leather Supplier'})
        cls.bank = cls.env['res.bank'].create({'name': 'Test Bank'})
        cls.manager = new_test_user(cls.env, login='lc_manager_t',
                                    groups='base.group_user,nelsis_lc_management.group_lc_manager')
        cls.officer = new_test_user(cls.env, login='lc_officer_t',
                                    groups='base.group_user,nelsis_lc_management.group_lc_officer')
        cls.lc_user = new_test_user(cls.env, login='lc_user_t',
                                    groups='base.group_user,nelsis_lc_management.group_lc_user')
        cls.auditor = new_test_user(cls.env, login='lc_auditor_t',
                                    groups='base.group_user,nelsis_lc_management.group_lc_auditor')
        cls.bond = new_test_user(cls.env, login='lc_bond_t',
                                 groups='base.group_user,nelsis_lc_management.group_lc_bond_officer')

    # ----------------------------------------------------------------- helpers
    def _new_lc(self, amount=10000.0, **kw):
        vals = {
            'partner_id': self.supplier.id,
            'bank_id': self.bank.id,
            'original_amount': amount,
            'lc_number': kw.pop('lc_number', 'LCNO-%s' % self.env['nelsis.lc'].search_count([])),
            'opening_date': self.today,
            'expiry_date': self.today + timedelta(days=90),
            'shipment_deadline': self.today + timedelta(days=60),
        }
        vals.update(kw)
        return self.env['nelsis.lc'].with_user(self.manager).create(vals)

    def _open_lc(self, **kw):
        lc = self._new_lc(**kw)
        lc.action_submit()
        lc.action_approve()
        lc.action_open()
        return lc

    def _shipment(self, lc, value=3000.0, **kw):
        vals = {'lc_id': lc.id, 'invoice_value': value, 'invoice_no': 'INV-1',
                'bl_awb_no': 'BL-1', 'shipment_date': self.today}
        vals.update(kw)
        return self.env['nelsis.lc.shipment'].with_user(self.manager).create(vals)

    def _receipt(self):
        wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        product = self.env['product.product'].create({'name': 'Test Hide', 'detailed_type': 'product'})
        picking = self.env['stock.picking'].create({
            'picking_type_id': wh.in_type_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': wh.lot_stock_id.id,
            'partner_id': self.supplier.id,
            'move_ids': [(0, 0, {
                'name': product.name, 'product_id': product.id, 'product_uom_qty': 5.0,
                'product_uom': product.uom_id.id,
                'location_id': self.env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': wh.lot_stock_id.id,
            })],
        })
        return picking, product

    # ----------------------------------------------------------------- workflow
    def test_01_workflow_and_log(self):
        lc = self._new_lc()
        self.assertEqual(lc.state, 'draft')
        self.assertTrue(lc.name.startswith('LC/'))
        lc.action_submit()
        self.assertEqual(lc.state, 'review')
        lc.action_approve()
        self.assertEqual(lc.state, 'approved')
        self.assertTrue(lc.approved_by_id)
        self.assertTrue(lc.approved_on)
        lc.action_open()
        self.assertEqual(lc.state, 'opened')
        self.assertGreaterEqual(len(lc.log_ids), 4)

    def test_02_state_cannot_be_written_directly(self):
        lc = self._new_lc()
        with self.assertRaises(UserError):
            lc.with_user(self.manager).write({'state': 'approved'})

    def test_03_date_validation(self):
        with self.assertRaises(ValidationError):
            self._new_lc(expiry_date=self.today - timedelta(days=1))
        with self.assertRaises(ValidationError):
            self._new_lc(shipment_deadline=self.today + timedelta(days=200))

    def test_04_locked_fields_after_draft(self):
        lc = self._open_lc()
        with self.assertRaises(UserError):
            lc.with_user(self.manager).write({'original_amount': 99999.0})
        with self.assertRaises(UserError):
            lc.with_user(self.manager).write({'expiry_date': self.today + timedelta(days=120)})

    # ----------------------------------------------------------------- amendments
    def test_10_amendment_flow_preserves_history(self):
        lc = self._open_lc()
        old_expiry = lc.expiry_date
        amd = self.env['nelsis.lc.amendment'].with_user(self.manager).create({
            'lc_id': lc.id, 'amount_change': 2000.0,
            'new_expiry_date': old_expiry + timedelta(days=30), 'reason': 'Extension',
        })
        self.assertEqual(amd.sequence_no, 1)
        amd.action_submit()
        self.assertEqual(lc.current_amount, 10000.0, 'Pending amendment must not count')
        amd.action_approve()
        self.assertEqual(lc.current_amount, 12000.0)
        self.assertEqual(lc.expiry_date, old_expiry + timedelta(days=30))
        self.assertEqual(amd.prev_amount, 10000.0)
        self.assertEqual(amd.new_amount, 12000.0)
        self.assertEqual(amd.prev_expiry_date, old_expiry)
        with self.assertRaises(UserError):
            amd.with_user(self.manager).write({'amount_change': 1.0})

    def test_11_amendment_cannot_go_below_utilized(self):
        lc = self._open_lc()
        sh = self._shipment(lc, 8000.0)
        sh.action_ship()
        amd = self.env['nelsis.lc.amendment'].with_user(self.manager).create({
            'lc_id': lc.id, 'amount_change': -5000.0, 'reason': 'Reduce'})
        amd.action_submit()
        with self.assertRaises(UserError):
            amd.action_approve()

    def test_12_officer_cannot_approve_amendment(self):
        lc = self._open_lc()
        amd = self.env['nelsis.lc.amendment'].with_user(self.officer).create({
            'lc_id': lc.id, 'amount_change': 500.0, 'reason': 'Top up'})
        amd.with_user(self.officer).action_submit()
        with self.assertRaises(AccessError):
            amd.with_user(self.officer).action_approve()

    # ----------------------------------------------------------------- shipments / utilization
    def test_20_partial_shipments_and_balance(self):
        lc = self._open_lc()
        s1 = self._shipment(lc, 4000.0)
        s2 = self._shipment(lc, 3000.0, invoice_no='INV-2', bl_awb_no='BL-2')
        self.assertEqual(lc.utilized_amount, 0.0)
        self.assertEqual(lc.planned_amount, 7000.0)
        self.assertEqual(lc.state, 'in_progress')
        s1.action_ship()
        self.assertEqual(lc.utilized_amount, 4000.0)
        self.assertEqual(lc.balance_amount, 6000.0)
        s2.action_ship()
        self.assertEqual(lc.balance_amount, 3000.0)
        self.assertAlmostEqual(lc.utilization_percent, 70.0)
        s2._do_cancel('Supplier cancelled')
        self.assertEqual(lc.balance_amount, 6000.0)

    def test_21_over_utilization_blocked(self):
        lc = self._open_lc()
        s = self._shipment(lc, 10500.0)
        with self.assertRaises(ValidationError):
            s.action_ship()

    def test_22_tolerance_allows_over_utilization(self):
        lc = self._open_lc(tolerance_percent=5.0)
        s = self._shipment(lc, 10400.0)
        s.action_ship()
        self.assertEqual(lc.utilized_amount, 10400.0)

    def test_23_shipment_requires_active_lc(self):
        lc = self._new_lc()
        with self.assertRaises(UserError):
            self.env['nelsis.lc.shipment'].with_user(self.officer).create(
                {'lc_id': lc.id, 'invoice_value': 1.0})

    def test_24_clearance_needs_boe_when_configured(self):
        lc = self._open_lc()
        s = self._shipment(lc, 1000.0)
        s.action_ship()
        s.action_docs_received()
        with self.assertRaises(UserError):
            s.action_clear()
        boe = self.env['nelsis.lc.boe'].with_user(self.manager).create({
            'name': 'BOE-1', 'lc_id': lc.id, 'shipment_id': s.id, 'boe_date': self.today})
        boe.action_submit()
        boe.clearance_date = self.today
        boe.action_clear()
        s.action_clear()
        self.assertEqual(s.state, 'customs_cleared')
        self.assertEqual(lc.state, 'partial')

    # ----------------------------------------------------------------- closure
    def test_30_close_blocked_by_pending_documents(self):
        lc = self._open_lc()
        dtype = self.env['nelsis.lc.document.type'].create(
            {'name': 'Test Doc', 'scope': 'lc', 'required_default': True})
        lc.action_load_required_documents()
        doc = lc.document_ids.filtered(lambda d: d.type_id == dtype)
        self.assertTrue(doc)
        with self.assertRaises(UserError):
            lc.action_close()
        doc.action_mark_received()
        lc.action_close()
        self.assertEqual(lc.state, 'closed')
        with self.assertRaises(UserError):
            lc.with_user(self.manager).write({'note': 'edit after close'})

    # ----------------------------------------------------------------- security
    def test_40_user_cannot_approve(self):
        lc = self._new_lc()
        lc.action_submit()
        with self.assertRaises(AccessError):
            lc.with_user(self.lc_user).action_approve()
        with self.assertRaises(AccessError):
            lc.with_user(self.officer).action_approve()

    def test_41_maker_checker_policy(self):
        lc = self._new_lc()
        lc._setting().enforce_maker_checker = True
        lc.action_submit()
        with self.assertRaises(UserError):
            lc.with_user(self.manager).action_approve()

    def test_42_auditor_read_only(self):
        lc = self._new_lc()
        self.assertTrue(lc.with_user(self.auditor).name)
        with self.assertRaises(AccessError):
            lc.with_user(self.auditor).write({'note': 'x'})

    def test_43_bond_officer_cannot_see_draft(self):
        draft = self._new_lc()
        opened = self._open_lc()
        visible = self.env['nelsis.lc'].with_user(self.bond).search([('id', 'in', (draft | opened).ids)])
        self.assertEqual(visible, opened)

    def test_44_lc_user_sees_only_own(self):
        own = self.env['nelsis.lc'].with_user(self.lc_user).create(
            {'partner_id': self.supplier.id, 'original_amount': 1.0})
        other = self._new_lc()
        visible = self.env['nelsis.lc'].with_user(self.lc_user).search([('id', 'in', (own | other).ids)])
        self.assertEqual(visible, own)

    def test_45_audit_log_is_immutable(self):
        lc = self._new_lc()
        with self.assertRaises(UserError):
            lc.log_ids[:1].write({'event': 'tampered'})
        with self.assertRaises(UserError):
            lc.log_ids[:1].unlink()

    def test_46_only_draft_can_be_deleted(self):
        lc = self._open_lc()
        with self.assertRaises(UserError):
            lc.unlink()

    # ----------------------------------------------------------------- stock integration
    def test_50_receipt_link_creates_no_stock(self):
        lc = self._open_lc()
        sh = self._shipment(lc, 1000.0)
        picking, product = self._receipt()
        moves_before = self.env['stock.move'].search_count([])
        quants_before = self.env['stock.quant'].search_count([('product_id', '=', product.id)])
        picking.with_user(self.manager).sudo().write({'lc_id': lc.id, 'lc_shipment_id': sh.id})
        self.assertEqual(lc.picking_count, 1)
        self.assertEqual(sh.picking_count, 1)
        self.assertEqual(self.env['stock.move'].search_count([]), moves_before)
        self.assertEqual(self.env['stock.quant'].search_count([('product_id', '=', product.id)]), quants_before)
        self.assertEqual(picking.state, 'draft', 'Linking must not confirm or validate the receipt')

    def test_51_link_requires_active_lc_and_receipt(self):
        draft_lc = self._new_lc()
        picking, _product = self._receipt()
        with self.assertRaises(ValidationError):
            picking.write({'lc_id': draft_lc.id})
        lc = self._open_lc()
        outgoing = self.env['stock.picking'].create({
            'picking_type_id': self.env['stock.warehouse'].search([], limit=1).out_type_id.id,
            'location_id': self.env['stock.warehouse'].search([], limit=1).lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        with self.assertRaises(ValidationError):
            outgoing.write({'lc_id': lc.id})

    def test_52_unauthorized_user_cannot_link(self):
        lc = self._open_lc()
        stock_user = new_test_user(self.env, login='plain_stock_t',
                                   groups='base.group_user,stock.group_stock_manager')
        picking, _product = self._receipt()
        with self.assertRaises(AccessError):
            picking.with_user(stock_user).write({'lc_id': lc.id})

    def test_53_received_requires_done_receipt(self):
        lc = self._open_lc()
        s = self._shipment(lc, 1000.0)
        s.action_ship()
        s.action_docs_received()
        s.sudo().write({'state': 'customs_cleared'})
        with self.assertRaises(UserError):
            s.action_receive()

    # ----------------------------------------------------------------- reminders
    def test_60_reminders_are_not_duplicated(self):
        lc = self._open_lc(expiry_date=self.today + timedelta(days=5),
                           shipment_deadline=self.today + timedelta(days=3))
        Lc = self.env['nelsis.lc']
        Lc._cron_lc_reminders()
        count1 = self.env['mail.activity'].search_count([('res_model', '=', 'nelsis.lc'), ('res_id', '=', lc.id)])
        self.assertGreaterEqual(count1, 1)
        Lc._cron_lc_reminders()
        count2 = self.env['mail.activity'].search_count([('res_model', '=', 'nelsis.lc'), ('res_id', '=', lc.id)])
        self.assertEqual(count1, count2)
        self.assertTrue(lc.expiry_reminded)
