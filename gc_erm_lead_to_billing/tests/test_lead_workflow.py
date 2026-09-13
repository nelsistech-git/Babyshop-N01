# -*- coding: utf-8 -*-
"""UAT-001, UAT-002, UAT-003 and the lead business rules (SRS 10, 11, 82)."""

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import GcErmCommon


@tagged('post_install', '-at_install', 'gc_erm')
class TestGcLeadWorkflow(GcErmCommon):

    def test_01_sequence_and_defaults(self):
        """A lead gets its configured sequence and starts in draft."""
        lead = self._create_lead(user=self.user_sales)
        self.assertTrue(lead.name.startswith('GC-LEAD-'),
                        'Lead number must follow the GC-LEAD- sequence.')
        self.assertEqual(lead.state, 'draft')
        self.assertTrue(lead.status_history_count >= 1,
                        'Creation must be recorded in the audit trail.')

    def test_02_submit_requires_mandatory_data(self):
        """SRS 10.1 -- the submit preconditions are enforced server side."""
        lead = self._create_lead(user=self.user_sales)
        lead.with_context(gc_bypass_lock=True).service_line_ids.unlink()
        with self.assertRaises(UserError):
            lead.with_user(self.user_sales).action_submit()

        lead2 = self._create_lead(user=self.user_sales, description=False)
        with self.assertRaises(UserError):
            lead2.with_user(self.user_sales).action_submit()

    def test_03_uat_001_submit_moves_to_hod(self):
        """UAT-001: submitting a lead sends it to HOD approval."""
        lead = self._create_lead(user=self.user_sales)
        lead.with_user(self.user_sales).action_submit()
        self.assertEqual(lead.state, 'hod_approval')
        self.assertEqual(lead.submitted_by_id, self.user_sales)
        self.assertTrue(lead.submitted_date)

    def test_04_sales_user_cannot_approve(self):
        """SRS 7.1 / BR-002 -- a sales user cannot approve a lead."""
        lead = self._create_lead(user=self.user_sales)
        lead.with_user(self.user_sales).action_submit()
        with self.assertRaises(AccessError):
            lead.with_user(self.user_sales).action_approve()

    def test_05_segregation_of_duties(self):
        """A HOD cannot approve a lead they submitted themselves."""
        lead = self._create_lead(user=self.user_hod, salesperson_id=self.user_hod.id)
        lead.with_user(self.user_hod).action_submit()
        with self.assertRaises(AccessError):
            lead.with_user(self.user_hod).action_approve()

    def test_06_uat_002_approval_enables_survey(self):
        """UAT-002: after HOD approval the survey can be created."""
        lead = self._approved_lead()
        self.assertEqual(lead.state, 'approved')
        self.assertEqual(lead.approved_by_id, self.user_hod)
        action = lead.with_user(self.user_sales).action_create_survey()
        self.assertEqual(action['res_model'], 'gc.erm.survey')

    def test_07_br_001_no_survey_before_approval(self):
        """BR-001 -- a survey cannot be created from an unapproved lead."""
        lead = self._create_lead(user=self.user_sales)
        with self.assertRaises(UserError):
            lead.with_user(self.user_sales).action_create_survey()
        lead.with_user(self.user_sales).action_submit()
        with self.assertRaises(UserError):
            lead.with_user(self.user_sales).action_create_survey()

    def test_08_uat_003_survey_inherits_lead_data(self):
        """UAT-003: the survey inherits customer and service information."""
        lead = self._approved_lead()
        action = lead.with_user(self.user_sales).action_create_survey()
        survey = self.env['gc.erm.survey'].browse(action['res_id'])
        self.assertEqual(survey.partner_id, lead.partner_id)
        self.assertEqual(survey.contact_id, lead.contact_id)
        self.assertEqual(survey.district, lead.district)
        self.assertEqual(survey.gps_latitude, lead.gps_latitude)
        self.assertEqual(len(survey.service_line_ids), len(lead.service_line_ids))
        self.assertEqual(survey.service_line_ids.service_id,
                         lead.service_line_ids.service_id)

    def test_09_rejection_requires_reason(self):
        """SRS 11 -- rejecting is only possible through the reason wizard."""
        lead = self._create_lead(user=self.user_sales)
        lead.with_user(self.user_sales).action_submit()
        wizard = self.env['gc.erm.reason.wizard'].with_user(self.user_hod).create({
            'mode': 'reject',
            'res_model': 'gc.erm.lead',
            'res_id': lead.id,
            'reason': '   ',
        })
        with self.assertRaises(UserError):
            wizard.action_confirm()
        wizard.reason = 'Customer is not creditworthy.'
        wizard.action_confirm()
        self.assertEqual(lead.state, 'rejected')
        self.assertEqual(lead.rejection_reason, 'Customer is not creditworthy.')
        self.assertEqual(lead.rejected_by_id, self.user_hod)

    def test_10_revision_returns_to_sales(self):
        """SRS 11 -- a revision sends the lead back to draft with a comment."""
        lead = self._create_lead(user=self.user_sales)
        lead.with_user(self.user_sales).action_submit()
        self.env['gc.erm.reason.wizard'].with_user(self.user_hod).create({
            'mode': 'revision',
            'res_model': 'gc.erm.lead',
            'res_id': lead.id,
            'reason': 'Please attach the LOI.',
        }).action_confirm()
        self.assertEqual(lead.state, 'draft')
        self.assertEqual(lead.revision_reason, 'Please attach the LOI.')
        # Sales can correct and resubmit.
        lead.with_user(self.user_sales).action_submit()
        self.assertEqual(lead.state, 'hod_approval')

    def test_11_approved_lead_is_locked(self):
        """SRS 67 -- commercial data of an approved lead cannot be edited."""
        lead = self._approved_lead()
        with self.assertRaises(UserError):
            lead.with_user(self.user_sales).write({'expected_revenue': 1.0})

    def test_12_no_direct_state_jump(self):
        """SRS 67 -- a draft lead cannot jump straight to approved."""
        lead = self._create_lead(user=self.user_sales)
        with self.assertRaises(UserError):
            lead.with_user(self.user_hod).action_approve()

    def test_13_audit_trail_is_complete(self):
        """SRS 62 / BR-010 -- every transition is logged with its author."""
        lead = self._approved_lead()
        history = self.env['gc.erm.status.history'].search([
            ('model_name', '=', 'gc.erm.lead'), ('res_id', '=', lead.id),
        ], order='id asc')
        states = history.mapped('new_state')
        self.assertIn('hod_approval', states)
        self.assertIn('approved', states)
        approval = history.filtered(lambda h: h.new_state == 'approved')
        self.assertEqual(approval.user_id, self.user_hod)
        with self.assertRaises(UserError):
            approval.with_user(self.user_hod).write({'comment': 'tampered'})

    def test_14_sla_deadline_is_set(self):
        """SRS 81 -- an SLA deadline is computed on submission."""
        lead = self._create_lead(user=self.user_sales)
        lead.with_user(self.user_sales).action_submit()
        self.assertTrue(lead.sla_deadline)
        self.assertEqual(lead.sla_state, 'on_time')

    def test_15_gps_validation(self):
        """SRS 66 -- GPS coordinates are validated."""
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self._create_lead(user=self.user_sales, gps_latitude=120.0)

    def test_16_cancel_and_reset(self):
        lead = self._create_lead(user=self.user_sales)
        lead.with_user(self.user_sales).action_cancel()
        self.assertEqual(lead.state, 'cancelled')
        lead.with_user(self.user_sales).action_reset_draft()
        self.assertEqual(lead.state, 'draft')

    def test_17_lead_smart_button_counts(self):
        lead = self._approved_lead()
        lead.with_user(self.user_sales).action_create_survey()
        lead.invalidate_recordset()
        self.assertEqual(lead.survey_count, 1)
        self.assertEqual(lead.work_order_count, 0)

    def test_18_deletion_blocked_after_approval(self):
        """SRS 62 -- an approved document cannot be deleted."""
        lead = self._approved_lead()
        with self.assertRaises(UserError):
            lead.with_user(self.user_admin).unlink()
