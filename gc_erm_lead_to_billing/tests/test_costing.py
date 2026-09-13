# -*- coding: utf-8 -*-
"""UAT-004, UAT-005 and the costing rules (SRS 15 - 20, 82)."""

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import GcErmCommon


@tagged('post_install', '-at_install', 'gc_erm')
class TestGcCosting(GcErmCommon):

    # ------------------------------------------------------------------
    # Survey / feasibility
    # ------------------------------------------------------------------
    def test_01_uat_004_survey_assignment_and_execution(self):
        survey = self._completed_survey()
        self.assertEqual(survey.state, 'in_progress')
        self.assertEqual(survey.engineer_id, self.user_engineer)
        self.assertTrue(survey.deadline)

    def test_02_feasibility_conditional_fields(self):
        """SRS 16 -- reason / conditions are mandatory for some outcomes."""
        survey = self._completed_survey()
        survey.with_user(self.user_engineer).write({
            'feasibility': 'not_feasible', 'feasibility_reason': False})
        with self.assertRaises(UserError):
            survey.with_user(self.user_engineer).action_complete()
        survey.with_user(self.user_engineer).feasibility_reason = 'No fibre route.'
        survey.with_user(self.user_engineer).action_complete()
        self.assertEqual(survey.state, 'completed')

    def test_03_feasibility_conditional_requires_conditions(self):
        survey = self._completed_survey()
        survey.with_user(self.user_engineer).write({'feasibility': 'conditional'})
        with self.assertRaises(UserError):
            survey.with_user(self.user_engineer).action_complete()

    # ------------------------------------------------------------------
    # UAT-005: costing formula (SRS 18)
    # ------------------------------------------------------------------
    def test_04_uat_005_cost_percentage_method(self):
        """Material + install + transport + other, then a margin on cost."""
        survey = self._completed_survey()
        boq = self._boq_for(survey, 'cost_pct', 25.0)

        router = boq.line_ids.filtered(lambda l: l.product_id == self.product_router)
        fiber = boq.line_ids.filtered(lambda l: l.product_id == self.product_fiber)

        self.assertAlmostEqual(router.material_cost, 40000.0, 2)
        self.assertAlmostEqual(router.line_cost, 44500.0, 2)
        self.assertAlmostEqual(router.margin_amount, 11125.0, 2)

        self.assertAlmostEqual(fiber.material_cost, 9000.0, 2)
        self.assertAlmostEqual(fiber.line_cost, 11000.0, 2)
        self.assertAlmostEqual(fiber.margin_amount, 2750.0, 2)

        self.assertAlmostEqual(boq.total_cost, 55500.0, 2)
        self.assertAlmostEqual(boq.total_margin, 13875.0, 2)
        self.assertAlmostEqual(boq.amount_untaxed, 69375.0, 2)
        self.assertAlmostEqual(boq.margin_percentage, 20.0, 2)

    def test_05_fixed_margin_method(self):
        survey = self._completed_survey()
        boq = self._boq_for(survey, 'fixed', 5000.0)
        self.assertAlmostEqual(boq.total_margin, 10000.0, 2,
                               'A fixed margin applies per line.')
        self.assertAlmostEqual(boq.amount_untaxed, 65500.0, 2)

    def test_06_price_percentage_method(self):
        """A 20% margin on selling price means margin/price == 20%."""
        survey = self._completed_survey()
        boq = self._boq_for(survey, 'price_pct', 20.0)
        self.assertAlmostEqual(boq.amount_untaxed, 55500.0 / 0.8, 2)
        self.assertAlmostEqual(boq.margin_percentage, 20.0, 2)

    def test_07_global_discount(self):
        survey = self._completed_survey()
        boq = self._boq_for(survey, 'cost_pct', 25.0)
        boq.with_user(self.user_engineer).global_discount = 10.0
        self.assertAlmostEqual(boq.amount_untaxed, 69375.0 * 0.9, 2)

    def test_08_line_discount(self):
        survey = self._completed_survey()
        boq = self._boq_for(survey, 'cost_pct', 25.0)
        router = boq.line_ids.filtered(lambda l: l.product_id == self.product_router)
        router.with_user(self.user_engineer).discount = 10.0
        self.assertAlmostEqual(router.price_subtotal, 55625.0 * 0.9, 2)

    def test_09_negative_and_zero_values_rejected(self):
        survey = self._completed_survey()
        boq = self._boq_for(survey)
        line = boq.line_ids[0]
        with self.assertRaises(ValidationError):
            line.with_user(self.user_engineer).quantity = 0.0
        with self.assertRaises(ValidationError):
            line.with_user(self.user_engineer).discount = 150.0
        with self.assertRaises(ValidationError):
            line.with_user(self.user_engineer).unit_cost = -1.0

    def test_10_margin_on_price_must_stay_below_100(self):
        survey = self._completed_survey()
        boq = self._boq_for(survey)
        with self.assertRaises(ValidationError):
            boq.with_user(self.user_engineer).write({
                'margin_method': 'price_pct', 'margin_value': 100.0})

    # ------------------------------------------------------------------
    # Costing controls (SRS 19)
    # ------------------------------------------------------------------
    def test_11_boq_locked_after_report_submission(self):
        report = self._submitted_technical_report()
        boq = report.boq_id
        self.assertEqual(boq.state, 'locked')
        with self.assertRaises(UserError):
            boq.with_user(self.user_engineer).write({'margin_value': 99.0})
        with self.assertRaises(UserError):
            boq.line_ids[0].with_user(self.user_engineer).unit_cost = 1.0

    def test_12_controlled_revision_keeps_history(self):
        """SRS 19 / 61 -- a revision creates v2 and preserves v1."""
        report = self._submitted_technical_report()
        boq = report.boq_id
        action = boq.with_user(self.user_engineer).action_create_revision()
        revision = self.env['gc.erm.boq'].browse(action['res_id'])
        self.assertEqual(revision.version, 2)
        self.assertEqual(revision.state, 'draft')
        self.assertEqual(revision.revision_of_id, boq)
        self.assertEqual(boq.state, 'revised')
        self.assertAlmostEqual(revision.total_cost, boq.total_cost, 2,
                               'The revision starts from the previous costing.')
        # v1 remains readable.
        self.assertTrue(boq.exists())
        self.assertEqual(boq.revision_count, 1)

    def test_13_sales_cannot_edit_confirmed_costing(self):
        """SRS 19 -- Sales must not change a confirmed technical costing."""
        survey = self._completed_survey()
        boq = self._boq_for(survey)
        boq.with_user(self.user_engineer).action_confirm()
        with self.assertRaises(UserError):
            boq.with_user(self.user_sales).write({'margin_value': 5.0})

    # ------------------------------------------------------------------
    # Technical report (SRS 20 / 21 / BR-004)
    # ------------------------------------------------------------------
    def test_14_report_requires_costing(self):
        """BR-004 -- costing must exist before the report is submitted."""
        survey = self._completed_survey()
        survey.with_user(self.user_engineer).action_complete()
        action = survey.with_user(self.user_engineer).action_create_technical_report()
        report = self.env['gc.erm.technical.report'].browse(action['res_id'])
        report.with_user(self.user_engineer).write(
            {'boq_id': False, 'feasibility': 'feasible'})
        with self.assertRaises(UserError):
            report.with_user(self.user_engineer).action_submit()

    def test_15_report_submission_notifies_sales(self):
        report = self._submitted_technical_report()
        self.assertEqual(report.state, 'submitted')
        self.assertEqual(report.survey_id.state, 'submitted')
        self.assertTrue(report.salesperson_id)
        self.assertAlmostEqual(report.total_cost, 55500.0, 2)
        self.assertAlmostEqual(report.amount_untaxed, 69375.0, 2)

    def test_16_not_feasible_blocks_proposal(self):
        survey = self._completed_survey()
        survey.with_user(self.user_engineer).write({
            'feasibility': 'not_feasible',
            'feasibility_reason': 'No route available.'})
        survey.with_user(self.user_engineer).action_complete()
        action = survey.with_user(self.user_engineer).action_create_technical_report()
        report = self.env['gc.erm.technical.report'].browse(action['res_id'])
        report.with_user(self.user_engineer).write({
            'feasibility': 'not_feasible',
            'technical_risks': 'No fibre within 5 km.'})
        report.with_user(self.user_engineer).action_submit()
        self.assertEqual(report.state, 'submitted')
        with self.assertRaises(UserError):
            report.with_user(self.user_sales).action_create_proposal()
