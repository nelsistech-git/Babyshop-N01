# -*- coding: utf-8 -*-
"""UAT-009, UAT-010, UAT-011 -- work order, inventory, procurement, delivery."""

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import GcErmCommon


@tagged('post_install', '-at_install', 'gc_erm')
class TestGcOperations(GcErmCommon):

    def test_01_br_006_work_order_needs_confirmed_order(self):
        """BR-006 -- customer acceptance is required before the work order."""
        proposal = self._approved_proposal()
        proposal.with_user(self.user_sales).action_create_quotation()
        order = proposal.sale_order_id
        self.assertEqual(order.state, 'draft')
        with self.assertRaises(UserError):
            order.with_user(self.user_sales).action_gc_create_work_order()

    def test_02_work_order_generated_from_sale_order(self):
        work_order = self._confirmed_work_order()
        self.assertTrue(work_order.name.startswith('GC-WO-'))
        self.assertEqual(work_order.sale_order_id.state, 'sale')
        self.assertEqual(work_order.partner_id, self.partner)
        self.assertTrue(work_order.lead_id)
        self.assertTrue(work_order.boq_id)
        self.assertTrue(work_order.line_ids,
                        'Material lines must be loaded from the BOQ.')

    def test_03_uat_009_inventory_shortage_detected(self):
        """UAT-009 -- available and shortage quantities are displayed."""
        work_order = self._confirmed_work_order()
        work_order.action_check_inventory()
        self.assertEqual(work_order.material_state, 'shortage')
        self.assertGreater(work_order.total_shortage_qty, 0.0)
        router_line = work_order.line_ids.filtered(
            lambda l: l.product_id == self.product_router)
        self.assertEqual(router_line.required_qty, 1.0)
        self.assertEqual(router_line.shortage_qty, 1.0)
        self.assertEqual(router_line.availability, 'shortage')
        self.assertEqual(work_order.state, 'material_pending')

    def test_04_shortage_formula(self):
        """SRS 30 -- Shortage = Required - Available, never negative."""
        self._stock_in(self.product_router, 5.0)
        work_order = self._confirmed_work_order()
        work_order.action_check_inventory()
        router_line = work_order.line_ids.filtered(
            lambda l: l.product_id == self.product_router)
        self.assertEqual(router_line.available_qty, 5.0)
        self.assertEqual(router_line.shortage_qty, 0.0)
        self.assertEqual(router_line.availability, 'available')

    def test_05_no_shortage_when_stock_is_available(self):
        self._stock_in(self.product_router, 10.0)
        self._stock_in(self.product_fiber, 1000.0)
        work_order = self._confirmed_work_order()
        work_order.action_check_inventory()
        self.assertNotEqual(work_order.material_state, 'shortage')
        self.assertEqual(work_order.total_shortage_qty, 0.0)
        # Material is available, but the work order still waits for its team
        # assignment before it becomes ready for installation (SRS 28).
        self.assertEqual(work_order.state, 'ready')
        work_order.action_set_ready_for_installation()
        self.assertEqual(work_order.state, 'ready_install')

    def test_06_uat_010_procurement_request_created(self):
        """UAT-010 -- a shortage generates a procurement request (BR-007)."""
        work_order = self._confirmed_work_order()
        action = work_order.with_user(self.user_impl).action_create_procurement_request()
        request = self.env['gc.erm.procurement.request'].browse(action['res_id'])
        self.assertTrue(request.name.startswith('GC-PR-'))
        self.assertEqual(request.work_order_id, work_order)
        self.assertEqual(len(request.line_ids), 2)
        for line in request.line_ids:
            self.assertGreater(line.shortage_qty, 0.0)

    def test_07_no_procurement_without_shortage(self):
        self._stock_in(self.product_router, 10.0)
        self._stock_in(self.product_fiber, 1000.0)
        work_order = self._confirmed_work_order()
        with self.assertRaises(UserError):
            work_order.with_user(self.user_impl).action_create_procurement_request()

    def test_08_procurement_to_purchase_order(self):
        """SRS 33 -- the request generates a standard purchase.order."""
        work_order = self._confirmed_work_order()
        action = work_order.with_user(self.user_impl).action_create_procurement_request()
        request = self.env['gc.erm.procurement.request'].browse(action['res_id'])
        request.with_user(self.user_impl).action_submit()
        self.assertEqual(request.state, 'submitted')

        wizard = self.env['gc.erm.procurement.po.wizard'].with_user(
            self.user_purchase).create({
                'request_id': request.id,
                'vendor_id': self.vendor.id,
                'date_planned': fields.Datetime.now(),
                'line_ids': [(6, 0, request.line_ids.ids)],
                'confirm_order': True,
            })
        po_action = wizard.action_create_rfq()
        purchase = self.env['purchase.order'].browse(po_action['res_id'])
        self.assertEqual(purchase._name, 'purchase.order')
        self.assertEqual(purchase.gc_procurement_id, request)
        self.assertEqual(purchase.gc_work_order_id, work_order)
        self.assertEqual(purchase.state, 'purchase')
        self.assertEqual(len(purchase.order_line), 2)
        self.assertEqual(request.state, 'po')
        # Each purchase line keeps the link back to the procurement line.
        for line in purchase.order_line:
            self.assertTrue(line.gc_procurement_line_id)

    def test_09_receipt_closes_procurement(self):
        work_order = self._confirmed_work_order()
        action = work_order.with_user(self.user_impl).action_create_procurement_request()
        request = self.env['gc.erm.procurement.request'].browse(action['res_id'])
        request.with_user(self.user_impl).action_submit()
        self.env['gc.erm.procurement.po.wizard'].with_user(
            self.user_purchase).create({
                'request_id': request.id,
                'vendor_id': self.vendor.id,
                'date_planned': fields.Datetime.now(),
                'line_ids': [(6, 0, request.line_ids.ids)],
                'confirm_order': True,
            }).action_create_rfq()
        purchase = request.purchase_order_ids[0]
        receipt = purchase.picking_ids[0]
        self.assertEqual(self._validate_picking(receipt), 'done')
        request.action_check_receipt()
        self.assertEqual(request.state, 'received')
        self.assertAlmostEqual(request.receipt_progress, 100.0, 1)
        work_order.action_check_inventory()
        self.assertNotEqual(work_order.material_state, 'shortage')

    def test_10_uat_011_delivery_uses_native_picking(self):
        """UAT-011 -- once materials exist, the delivery makes the WO ready."""
        self._stock_in(self.product_router, 10.0)
        self._stock_in(self.product_fiber, 1000.0)
        work_order = self._confirmed_work_order()
        work_order.action_create_delivery()
        self.assertTrue(work_order.picking_ids)
        picking = work_order.picking_ids[0]
        self.assertEqual(picking._name, 'stock.picking')
        self.assertEqual(picking.picking_type_code, 'outgoing',
                         'Only outgoing transfers count as deliveries.')
        self.assertEqual(picking.gc_work_order_id, work_order)
        self.assertEqual(self._validate_picking(picking), 'done')
        work_order.invalidate_recordset()
        self.assertEqual(work_order.delivery_state, 'Done')
        self.assertEqual(work_order.material_state, 'delivered')

    def test_11_delivery_blocked_on_shortage(self):
        work_order = self._confirmed_work_order()
        with self.assertRaises(UserError):
            work_order.action_create_delivery()

    def test_12_receipts_are_not_counted_as_deliveries(self):
        """A purchase receipt linked to the WO must not look like a delivery."""
        work_order = self._confirmed_work_order()
        action = work_order.with_user(self.user_impl).action_create_procurement_request()
        request = self.env['gc.erm.procurement.request'].browse(action['res_id'])
        request.with_user(self.user_impl).action_submit()
        self.env['gc.erm.procurement.po.wizard'].with_user(
            self.user_purchase).create({
                'request_id': request.id,
                'vendor_id': self.vendor.id,
                'date_planned': fields.Datetime.now(),
                'line_ids': [(6, 0, request.line_ids.ids)],
                'confirm_order': True,
            }).action_create_rfq()
        receipt = request.purchase_order_ids[0].picking_ids[0]
        self._validate_picking(receipt)
        work_order.invalidate_recordset()
        self.assertEqual(work_order.receipt_count, 1)
        self.assertNotIn(receipt, work_order.picking_ids,
                         'The receipt must not appear as a delivery.')
        self.assertTrue(
            all(p.picking_type_code == 'outgoing' for p in work_order.picking_ids),
            'Only outgoing transfers may be listed as deliveries.')

    def test_13_team_assignment_and_notifications(self):
        work_order = self._confirmed_work_order()
        work_order.action_assign_team()
        self.assertIn(work_order.state, ('assigned', 'material_pending'))
        self.assertTrue(work_order.activity_ids,
                        'The assignment must schedule an activity.')

    def test_14_assignment_requires_a_team_or_engineer(self):
        work_order = self._confirmed_work_order()
        work_order.write({'team_id': False, 'engineer_id': False})
        with self.assertRaises(UserError):
            work_order.action_assign_team()

    def test_15_milestone_percentages_must_total_100(self):
        from odoo.exceptions import ValidationError
        work_order = self._confirmed_work_order()
        with self.assertRaises(ValidationError):
            work_order.write({
                'billing_policy': 'milestone',
                'advance_percent': 30.0,
                'installation_percent': 30.0,
                'completion_percent': 30.0,
            })

    def test_16_work_order_delay_cron(self):
        work_order = self._confirmed_work_order()
        work_order.write({
            'start_date': fields.Date.add(fields.Date.today(), days=-10),
            'expected_completion': fields.Date.add(fields.Date.today(), days=-3),
        })
        self.env['gc.erm.work.order']._cron_check_work_order_delay()
        self.assertTrue(work_order.is_delayed)
