# -*- coding: utf-8 -*-
"""Security testing: access rights, record rules and workflow guards
(SRS 67, 68, 89)."""

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import GcErmCommon


@tagged('post_install', '-at_install', 'gc_erm')
class TestGcSecurity(GcErmCommon):

    # ------------------------------------------------------------------
    # Access rights (ir.model.access.csv)
    # ------------------------------------------------------------------
    def test_01_technical_user_cannot_create_leads(self):
        with self.assertRaises(AccessError):
            self.env['gc.erm.lead'].with_user(self.user_engineer).create({
                'partner_id': self.partner.id,
                'salesperson_id': self.user_engineer.id,
            })

    def test_02_sales_user_cannot_create_boq(self):
        survey = self._completed_survey()
        with self.assertRaises(AccessError):
            self.env['gc.erm.boq'].with_user(self.user_sales).create({
                'survey_id': survey.id,
                'partner_id': self.partner.id,
            })

    def test_03_sales_can_read_boq(self):
        """Sales must see the costing result without being able to change it."""
        survey = self._completed_survey()
        boq = self._boq_for(survey)
        self.assertTrue(boq.with_user(self.user_sales).read(['amount_total']))

    def test_04_implementation_cannot_approve_proposals(self):
        report = self._submitted_technical_report()
        action = report.with_user(self.user_sales).action_create_proposal()
        proposal = self.env['gc.erm.proposal'].browse(action['res_id'])
        proposal.with_user(self.user_sales).action_submit()
        with self.assertRaises(AccessError):
            proposal.with_user(self.user_impl).action_approve()
        with self.assertRaises(AccessError):
            proposal.with_user(self.user_impl).write({'remarks': 'hack'})

    def test_05_accounts_cannot_edit_installation_result(self):
        with self.assertRaises(AccessError):
            self.env['gc.erm.installation'].with_user(self.user_accounts).create({
                'work_order_id': self._confirmed_work_order().id,
                'partner_id': self.partner.id,
                'engineer_id': self.user_accounts.id,
            })

    # ------------------------------------------------------------------
    # Record rules (SRS 68)
    # ------------------------------------------------------------------
    def test_06_sales_user_sees_only_own_leads(self):
        other_sales = self._create_user('gc_sales2', 'Sara Sales', self.group_sales)
        mine = self._create_lead(user=self.user_sales)
        theirs = self._create_lead(user=other_sales,
                                   salesperson_id=other_sales.id)
        visible = self.env['gc.erm.lead'].with_user(self.user_sales).search([])
        self.assertIn(mine, visible)
        self.assertNotIn(theirs, visible,
                         'A sales user must not see another rep\'s leads.')

    def test_07_hod_sees_all_leads(self):
        other_sales = self._create_user('gc_sales3', 'Sid Sales', self.group_sales)
        theirs = self._create_lead(user=other_sales,
                                   salesperson_id=other_sales.id)
        visible = self.env['gc.erm.lead'].with_user(self.user_hod).search([])
        self.assertIn(theirs, visible)

    def test_08_engineer_sees_assigned_surveys(self):
        survey = self._completed_survey()
        visible = self.env['gc.erm.survey'].with_user(self.user_engineer).search([])
        self.assertIn(survey, visible)

    def test_09_engineer_does_not_see_unassigned_surveys(self):
        other_eng = self._create_user('gc_eng2', 'Ed Engineer', self.group_tech)
        survey = self._completed_survey()
        visible = self.env['gc.erm.survey'].with_user(other_eng).search([])
        self.assertNotIn(survey, visible)

    def test_10_implementation_sees_assigned_work_orders(self):
        work_order = self._confirmed_work_order()
        work_order.write({'engineer_id': self.user_impl.id})
        visible = self.env['gc.erm.work.order'].with_user(self.user_impl).search([])
        self.assertIn(work_order, visible)

    def test_11_implementation_does_not_see_other_work_orders(self):
        other_impl = self._create_user('gc_impl2', 'Ivy Implementer',
                                       self.group_impl)
        work_order = self._confirmed_work_order()
        work_order.write({'engineer_id': self.user_impl.id,
                          'team_id': self.team_impl.id,
                          'manager_id': self.user_impl.id,
                          'technician_ids': [(6, 0, self.user_impl.ids)]})
        visible = self.env['gc.erm.work.order'].with_user(other_impl).search([])
        self.assertNotIn(work_order, visible)

    # ------------------------------------------------------------------
    # Workflow guards (SRS 67)
    # ------------------------------------------------------------------
    def test_12_cannot_skip_states(self):
        """A document cannot move directly from draft to completed."""
        work_order = self._confirmed_work_order()
        with self.assertRaises(UserError):
            work_order.action_complete()

    def test_13_installation_requires_ready_work_order(self):
        work_order = self._confirmed_work_order()
        # Still material_pending: no installation may be started.
        with self.assertRaises(UserError):
            work_order.with_user(self.user_impl).action_create_installation()

    def test_14_segregation_can_be_disabled(self):
        """The segregation of duties rule is a configuration switch."""
        self.env['ir.config_parameter'].sudo().set_param(
            'gc_erm.segregation_of_duties', 'False')
        lead = self._create_lead(user=self.user_hod,
                                 salesperson_id=self.user_hod.id)
        lead.with_user(self.user_hod).action_submit()
        lead.with_user(self.user_hod).action_approve()
        self.assertEqual(lead.state, 'approved')
        self.env['ir.config_parameter'].sudo().set_param(
            'gc_erm.segregation_of_duties', 'True')

    def test_15_audit_trail_is_append_only(self):
        lead = self._approved_lead()
        entry = self.env['gc.erm.status.history'].search(
            [('model_name', '=', 'gc.erm.lead'), ('res_id', '=', lead.id)], limit=1)
        with self.assertRaises(UserError):
            entry.with_user(self.user_hod).write({'comment': 'changed'})
        with self.assertRaises(UserError):
            entry.with_user(self.user_sales).unlink()

    def test_16_every_model_has_access_rules(self):
        """No ERM model may be left without an ir.model.access entry."""
        models = self.env['ir.model'].search([('model', 'like', 'gc.erm.%')])
        for model in models:
            if model.transient or not model.model.startswith('gc.erm.'):
                continue
            if self.env[model.model]._abstract:
                continue
            access = self.env['ir.model.access'].search_count(
                [('model_id', '=', model.id)])
            self.assertTrue(
                access, 'Model %s has no access rules defined.' % model.model)

    def test_17_management_is_read_only(self):
        """SRS 7.9 -- management reads everything but does not edit."""
        management = self._create_user(
            'gc_mgmt', 'Meg Management',
            self.env.ref('gc_erm_lead_to_billing.group_gc_management'))
        lead = self._approved_lead()
        self.assertTrue(lead.with_user(management).read(['name']))
        with self.assertRaises(AccessError):
            lead.with_user(management).write({'area': 'Banani'})
