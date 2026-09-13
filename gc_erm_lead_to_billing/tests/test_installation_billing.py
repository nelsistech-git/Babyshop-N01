# -*- coding: utf-8 -*-
"""UAT-012, UAT-013 -- installation, revisit and billing (SRS 36 - 44, 82)."""

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import GcErmCommon


@tagged('post_install', '-at_install', 'gc_erm')
class TestGcInstallationBilling(GcErmCommon):

    def _ready_work_order(self):
        self._stock_in(self.product_router, 10.0)
        self._stock_in(self.product_fiber, 1000.0)
        work_order = self._confirmed_work_order()
        work_order.write({
            'team_id': self.team_impl.id,
            'engineer_id': self.user_impl.id,
            'manager_id': self.user_impl.id,
        })
        work_order.action_create_delivery()
        self._validate_picking(work_order.picking_ids[0])
        work_order.action_set_ready_for_installation()
        return work_order

    def _installation(self, work_order=None):
        work_order = work_order or self._ready_work_order()
        action = work_order.with_user(self.user_impl).action_create_installation()
        return self.env['gc.erm.installation'].browse(action['res_id'])

    # ------------------------------------------------------------------
    # Installation
    # ------------------------------------------------------------------
    def test_01_br_008_installation_references_work_order(self):
        installation = self._installation()
        self.assertTrue(installation.name.startswith('GC-INS-'))
        self.assertTrue(installation.work_order_id)
        self.assertEqual(installation.partner_id, self.partner)

    def test_02_checklist_and_products_are_loaded(self):
        """SRS 37 -- the configured checklist is copied onto the record."""
        installation = self._installation()
        self.assertTrue(installation.checklist_line_ids)
        self.assertEqual(len(installation.checklist_line_ids), 13)
        self.assertTrue(installation.line_ids,
                        'Installed products come from the work order materials.')

    def test_03_report_requires_a_result(self):
        """SRS 38 -- no report without an installation result."""
        installation = self._installation()
        installation.with_user(self.user_impl).action_start()
        with self.assertRaises(UserError):
            installation.with_user(self.user_impl).action_submit_report()

    def test_04_failed_result_requires_follow_up_fields(self):
        installation = self._installation()
        installation.with_user(self.user_impl).action_start()
        installation.with_user(self.user_impl).result = 'failed'
        for line in installation.checklist_line_ids:
            line.answer = 'yes'
        with self.assertRaises(UserError):
            installation.with_user(self.user_impl).action_submit_report()
        installation.with_user(self.user_impl).write({
            'failure_reason': 'Power not available on site.',
            'required_action': 'Customer to provide UPS.',
            'next_visit_date': fields.Date.add(fields.Date.today(), days=2),
            'next_engineer_id': self.user_impl.id,
        })
        installation.with_user(self.user_impl).action_submit_report()
        self.assertEqual(installation.state, 'submitted')

    def test_05_mandatory_checklist_items(self):
        installation = self._installation()
        installation.with_user(self.user_impl).action_start()
        installation.with_user(self.user_impl).result = 'success'
        with self.assertRaises(UserError):
            installation.with_user(self.user_impl).action_submit_report()

    def test_06_uat_012_successful_installation(self):
        """UAT-012 -- a completed installation can be reported and closed."""
        work_order = self._ready_work_order()
        installation = self._installation(work_order)
        installation.with_user(self.user_impl).action_start()
        self.assertEqual(installation.state, 'in_progress')
        installation.with_user(self.user_impl).result = 'success'
        for line in installation.checklist_line_ids:
            line.answer = 'yes'
        installation.with_user(self.user_impl).write({
            'customer_representative': 'Mr Contact',
            'customer_accepted': True,
            'testing_results': '<p>10 Mbps verified.</p>',
        })
        installation.with_user(self.user_impl).action_submit_report()
        self.assertEqual(installation.state, 'submitted')
        self.assertTrue(installation.checklist_complete)
        installation.with_user(self.user_impl).action_complete()
        self.assertEqual(installation.state, 'done')
        work_order.invalidate_recordset()
        self.assertEqual(work_order.state, 'install_done')

    def test_07_failed_installation_cannot_be_completed(self):
        installation = self._installation()
        installation.with_user(self.user_impl).action_start()
        installation.with_user(self.user_impl).write({
            'result': 'failed',
            'failure_reason': 'No power.',
            'required_action': 'Provide UPS.',
            'next_visit_date': fields.Date.add(fields.Date.today(), days=2),
            'next_engineer_id': self.user_impl.id,
        })
        for line in installation.checklist_line_ids:
            line.answer = 'yes'
        installation.with_user(self.user_impl).action_submit_report()
        with self.assertRaises(UserError):
            installation.with_user(self.user_impl).action_complete()

    def test_08_revisit_preserves_previous_report(self):
        """SRS 40 -- a revisit creates a new visit, the old one is kept."""
        installation = self._installation()
        installation.with_user(self.user_impl).action_start()
        for line in installation.checklist_line_ids:
            line.answer = 'yes'
        wizard = self.env['gc.erm.revisit.wizard'].with_user(self.user_impl).create({
            'installation_id': installation.id,
            'reason': 'Customer rack was not ready.',
            'required_action': 'Return once the rack is installed.',
            'next_visit_date': fields.Date.add(fields.Date.today(), days=3),
            'engineer_id': self.user_impl.id,
            'team_id': self.team_impl.id,
        })
        action = wizard.action_create_revisit()
        revisit = self.env['gc.erm.installation'].browse(action['res_id'])
        self.assertEqual(revisit.revisit_of_id, installation)
        self.assertEqual(revisit.visit_number, 2)
        self.assertEqual(installation.state, 'revisit')
        self.assertTrue(installation.exists(),
                        'The previous report must be preserved.')
        self.assertEqual(installation.revisit_count, 1)
        self.assertTrue(revisit.checklist_line_ids)

    # ------------------------------------------------------------------
    # Billing (SRS 41 - 44)
    # ------------------------------------------------------------------
    def _completed_installation_work_order(self):
        work_order = self._ready_work_order()
        installation = self._installation(work_order)
        installation.with_user(self.user_impl).action_start()
        installation.with_user(self.user_impl).result = 'success'
        for line in installation.checklist_line_ids:
            line.answer = 'yes'
        installation.with_user(self.user_impl).action_submit_report()
        installation.with_user(self.user_impl).action_complete()
        work_order.invalidate_recordset()
        return work_order

    def test_09_br_009_billing_blocked_before_installation(self):
        work_order = self._ready_work_order()
        self.assertFalse(work_order.billing_ready)
        self.assertTrue(work_order.billing_blocked_reason)
        with self.assertRaises(UserError):
            work_order.with_user(self.user_accounts).action_open_invoice_wizard()

    def test_10_uat_013_invoice_after_installation(self):
        """UAT-013 -- once installation is complete the invoice can be made."""
        work_order = self._completed_installation_work_order()
        self.assertTrue(work_order.billing_ready, work_order.billing_blocked_reason)
        wizard = self.env['gc.erm.invoice.wizard'].with_user(
            self.user_accounts).create({
                'work_order_id': work_order.id,
                'milestone': 'full',
                'invoice_percent': 100.0,
                'invoice_date': fields.Date.today(),
                'post_invoice': True,
            })
        action = wizard.action_create_invoice()
        invoice = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(invoice._name, 'account.move')
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.gc_work_order_id, work_order)
        self.assertEqual(invoice.gc_milestone, 'full')
        self.assertTrue(invoice.gc_is_erm_invoice)
        self.assertGreater(invoice.amount_total, 0.0)

    def test_11_advance_billing_policy(self):
        """SRS 43 -- an advance invoice does not require an installation."""
        work_order = self._ready_work_order()
        work_order.write({'billing_policy': 'advance_final',
                          'advance_percent': 50.0})
        self.assertTrue(work_order.billing_ready)
        wizard = self.env['gc.erm.invoice.wizard'].with_user(
            self.user_accounts).create({
                'work_order_id': work_order.id,
                'milestone': 'advance',
                'invoice_percent': 50.0,
                'invoice_date': fields.Date.today(),
            })
        action = wizard.action_create_invoice()
        invoice = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(invoice.gc_milestone, 'advance')
        expected = work_order.sale_order_id.amount_untaxed * 0.5
        self.assertAlmostEqual(invoice.amount_untaxed, expected, delta=1.0)

    def test_12_milestone_billing(self):
        work_order = self._completed_installation_work_order()
        work_order.write({
            'billing_policy': 'milestone',
            'advance_percent': 30.0,
            'installation_percent': 40.0,
            'completion_percent': 30.0,
        })
        wizard = self.env['gc.erm.invoice.wizard'].with_user(
            self.user_accounts).create({
                'work_order_id': work_order.id,
                'milestone': 'installation',
                'invoice_percent': 40.0,
                'invoice_date': fields.Date.today(),
            })
        action = wizard.action_create_invoice()
        invoice = self.env['account.move'].browse(action['res_id'])
        expected = work_order.sale_order_id.amount_untaxed * 0.4
        self.assertAlmostEqual(invoice.amount_untaxed, expected, delta=1.0)

    def test_13_invoice_percent_validation(self):
        from odoo.exceptions import ValidationError
        work_order = self._completed_installation_work_order()
        with self.assertRaises(ValidationError):
            self.env['gc.erm.invoice.wizard'].with_user(self.user_accounts).create({
                'work_order_id': work_order.id,
                'milestone': 'full',
                'invoice_percent': 150.0,
                'invoice_date': fields.Date.today(),
            })

    def test_14_delivery_based_billing(self):
        work_order = self._ready_work_order()
        work_order.write({'billing_policy': 'delivery'})
        work_order.invalidate_recordset()
        self.assertTrue(work_order.billing_ready,
                        'The delivery is done, so billing is allowed.')

    def test_15_work_order_completion_and_traceability(self):
        work_order = self._completed_installation_work_order()
        self.env['gc.erm.invoice.wizard'].with_user(self.user_accounts).create({
            'work_order_id': work_order.id,
            'milestone': 'full',
            'invoice_percent': 100.0,
            'invoice_date': fields.Date.today(),
            'post_invoice': True,
        }).action_create_invoice()
        work_order.with_user(self.user_impl).action_complete()
        self.assertEqual(work_order.state, 'completed')
        self.assertTrue(work_order.actual_completion)
        lead = work_order.lead_id
        lead.invalidate_recordset()
        self.assertEqual(lead.work_order_count, 1)
        self.assertEqual(lead.invoice_count, 1)
        self.assertEqual(lead.survey_count, 1)
        self.assertEqual(lead.proposal_count, 1)

    def test_16_overdue_invoice_flag(self):
        work_order = self._completed_installation_work_order()
        action = self.env['gc.erm.invoice.wizard'].with_user(
            self.user_accounts).create({
                'work_order_id': work_order.id,
                'milestone': 'full',
                'invoice_percent': 100.0,
                'invoice_date': fields.Date.add(fields.Date.today(), days=-60),
                'post_invoice': True,
            }).action_create_invoice()
        invoice = self.env['account.move'].browse(action['res_id'])
        invoice.invoice_date_due = fields.Date.add(fields.Date.today(), days=-30)
        invoice._compute_gc_is_overdue()
        self.assertTrue(invoice.gc_is_overdue)
