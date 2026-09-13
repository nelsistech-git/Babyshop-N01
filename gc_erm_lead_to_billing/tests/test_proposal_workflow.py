# -*- coding: utf-8 -*-
"""UAT-006, UAT-007, UAT-008 -- proposal, approval, quotation, acceptance."""

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import GcErmCommon


@tagged('post_install', '-at_install', 'gc_erm')
class TestGcProposalWorkflow(GcErmCommon):

    def test_01_uat_006_proposal_inherits_technical_data(self):
        report = self._submitted_technical_report()
        action = report.with_user(self.user_sales).action_create_proposal()
        proposal = self.env['gc.erm.proposal'].browse(action['res_id'])
        self.assertEqual(proposal.technical_report_id, report)
        self.assertEqual(proposal.boq_id, report.boq_id)
        self.assertEqual(proposal.survey_id, report.survey_id)
        self.assertEqual(proposal.lead_id, report.lead_id)
        self.assertEqual(len(proposal.line_ids), len(report.boq_id.line_ids))
        # Pricing comes from the approved costing (rounded to the currency).
        self.assertAlmostEqual(proposal.amount_untaxed,
                               report.boq_id.amount_untaxed, delta=1.0)

    def test_02_proposal_requires_lines_and_validity(self):
        report = self._submitted_technical_report()
        action = report.with_user(self.user_sales).action_create_proposal()
        proposal = self.env['gc.erm.proposal'].browse(action['res_id'])
        proposal.with_user(self.user_sales).line_ids.unlink()
        with self.assertRaises(UserError):
            proposal.with_user(self.user_sales).action_submit()

    def test_03_uat_007_approval_enables_offer(self):
        proposal = self._approved_proposal()
        self.assertEqual(proposal.state, 'approved')
        self.assertEqual(proposal.approved_by_id, self.user_hod)
        proposal.with_user(self.user_sales).action_send_offer()
        self.assertEqual(proposal.state, 'sent')
        self.assertTrue(proposal.sale_order_id)

    def test_04_sales_cannot_approve_own_proposal(self):
        report = self._submitted_technical_report()
        action = report.with_user(self.user_sales).action_create_proposal()
        proposal = self.env['gc.erm.proposal'].browse(action['res_id'])
        proposal.with_user(self.user_sales).action_submit()
        with self.assertRaises(AccessError):
            proposal.with_user(self.user_sales).action_approve()

    def test_05_br_005_approved_proposal_is_locked(self):
        proposal = self._approved_proposal()
        with self.assertRaises(UserError):
            proposal.with_user(self.user_sales).write({'global_discount': 5.0})

    def test_06_revision_creates_new_version(self):
        """SRS 61 -- v1 stays accessible, v2 is editable."""
        proposal = self._approved_proposal()
        action = proposal.with_user(self.user_sales).action_create_revision()
        revision = self.env['gc.erm.proposal'].browse(action['res_id'])
        self.assertEqual(revision.version, 2)
        self.assertEqual(revision.state, 'draft')
        self.assertEqual(revision.revision_of_id, proposal)
        self.assertEqual(proposal.state, 'revised')
        self.assertTrue(proposal.exists())
        self.assertEqual(len(revision.line_ids), len(proposal.line_ids))

    def test_07_quotation_uses_standard_sale_order(self):
        """SRS 25 -- no parallel quotation engine."""
        proposal = self._approved_proposal()
        proposal.with_user(self.user_sales).action_create_quotation()
        order = proposal.sale_order_id
        self.assertTrue(order)
        self.assertEqual(order._name, 'sale.order')
        self.assertEqual(order.gc_proposal_id, proposal)
        self.assertEqual(order.gc_lead_id, proposal.lead_id)
        self.assertEqual(order.partner_id, proposal.partner_id)
        self.assertEqual(len(order.order_line), len(proposal.line_ids))
        self.assertEqual(order.state, 'draft')
        # Calling it twice must not create a second quotation.
        proposal.with_user(self.user_sales).action_create_quotation()
        self.assertEqual(
            self.env['sale.order'].search_count(
                [('gc_proposal_id', '=', proposal.id)]), 1)

    def test_08_uat_008_acceptance_confirms_order(self):
        proposal = self._approved_proposal()
        wizard = self.env['gc.erm.acceptance.wizard'].with_user(
            self.user_sales).create({
                'proposal_id': proposal.id,
                'method': 'internal',
                'acceptance_date': fields.Date.today(),
                'accepted_by': 'Mr Contact',
                'confirm_sale_order': True,
                'create_work_order': False,
            })
        wizard.action_confirm()
        self.assertEqual(proposal.state, 'accepted')
        self.assertEqual(proposal.accepted_by, 'Mr Contact')
        self.assertEqual(proposal.acceptance_method, 'internal')
        self.assertEqual(proposal.sale_order_id.state, 'sale')

    def test_09_signed_acceptance_requires_document(self):
        proposal = self._approved_proposal()
        wizard = self.env['gc.erm.acceptance.wizard'].with_user(
            self.user_sales).create({
                'proposal_id': proposal.id,
                'method': 'signed',
                'acceptance_date': fields.Date.today(),
                'accepted_by': 'Mr Contact',
            })
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_10_customer_refusal_cancels_quotation(self):
        proposal = self._approved_proposal()
        proposal.with_user(self.user_sales).action_create_quotation()
        proposal.with_user(self.user_sales).action_customer_refused()
        self.assertEqual(proposal.state, 'refused')
        self.assertEqual(proposal.sale_order_id.state, 'cancel')

    def test_11_confirming_order_marks_proposal_accepted(self):
        """Confirming the Odoo quotation directly is also an acceptance."""
        proposal = self._approved_proposal()
        proposal.with_user(self.user_sales).action_create_quotation()
        proposal.sale_order_id.with_user(self.user_sales).action_confirm()
        self.assertEqual(proposal.state, 'accepted')
        self.assertEqual(proposal.acceptance_method, 'quotation')

    def test_12_amount_based_approval_matrix(self):
        """SRS 60 -- a large proposal needs a higher approval level."""
        self.env['gc.erm.approval.matrix'].search(
            [('document_type', '=', 'proposal')]).write({'active': False})
        self.env['gc.erm.approval.matrix'].create({
            'document_type': 'proposal',
            'amount_from': 0.0,
            'amount_to': 1000.0,
            'approver_group_id': self.group_hod.id,
            'company_id': self.company.id,
        })
        self.env['gc.erm.approval.matrix'].create({
            'document_type': 'proposal',
            'amount_from': 1000.01,
            'amount_to': 0.0,
            'approver_group_id': self.group_admin.id,
            'company_id': self.company.id,
        })
        report = self._submitted_technical_report()
        action = report.with_user(self.user_sales).action_create_proposal()
        proposal = self.env['gc.erm.proposal'].browse(action['res_id'])
        proposal.with_user(self.user_sales).action_submit()
        # Way above 1000, so the plain HOD is not enough any more.
        with self.assertRaises(AccessError):
            proposal.with_user(self.user_hod).action_approve()
        proposal.with_user(self.user_admin).action_approve()
        self.assertEqual(proposal.state, 'approved')

    def test_13_proposal_expiry_cron(self):
        proposal = self._approved_proposal()
        proposal.with_context(gc_bypass_lock=True).write({
            'proposal_date': fields.Date.add(fields.Date.today(), days=-40),
            'validity_date': fields.Date.add(fields.Date.today(), days=-1),
        })
        self.env['gc.erm.proposal']._cron_expire_proposals()
        self.assertTrue(proposal.is_expired)

    def test_14_reject_with_reason(self):
        report = self._submitted_technical_report()
        action = report.with_user(self.user_sales).action_create_proposal()
        proposal = self.env['gc.erm.proposal'].browse(action['res_id'])
        proposal.with_user(self.user_sales).action_submit()
        self.env['gc.erm.reason.wizard'].with_user(self.user_hod).create({
            'mode': 'reject',
            'res_model': 'gc.erm.proposal',
            'res_id': proposal.id,
            'reason': 'Margin too low.',
        }).action_confirm()
        self.assertEqual(proposal.state, 'rejected')
        self.assertEqual(proposal.rejection_reason, 'Margin too low.')
