# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
from datetime import date

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import BondComplianceCommon


@tagged('post_install', '-at_install', 'nelsis_bond_compliance')
class TestComplianceEngine(BondComplianceCommon):

    def _active_rule(self, **extra):
        extra.setdefault('required_document_type_ids', [(6, 0, [self.doc_lc.id, self.doc_boe.id])])
        return self._activate(self._make_rule(**extra))

    def test_pass_when_values_and_documents_are_valid(self):
        rule = self._active_rule()
        res = self.engine.evaluate(
            'tst-rule-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY',
            values={'test_limit': 10}, documents=['LC_COPY', 'BILL_OF_ENTRY'])
        self.assertEqual(res['status'], 'passed')
        self.assertTrue(res['passed'])
        self.assertEqual(res['rule_id'], rule.id)
        self.assertEqual(res['rule_version'], 1)
        self.assertTrue(res['disclaimer'])

    def test_fail_on_parameter_and_missing_document(self):
        self._active_rule()
        res = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY',
            values={'test_limit': 11}, documents=['LC_COPY'])
        self.assertEqual(res['status'], 'failed')
        self.assertFalse(res['passed'])
        self.assertEqual(res['missing_document_types'], ['BILL_OF_ENTRY'])
        self.assertEqual(res['parameter_results'][0]['result'], 'fail')
        self.assertTrue(res['messages'])

    def test_documents_can_be_passed_as_records(self):
        self._active_rule()
        res = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY',
            values={'test_limit': 1}, documents=self.doc_lc | self.doc_boe)
        self.assertTrue(res['passed'])

    def test_required_input_missing_fails(self):
        self._active_rule(parameter_ids=[(0, 0, {
            'name': 'Limit', 'key': 'test_limit', 'value_type': 'integer', 'operator': 'le',
            'value_integer': 10, 'value_is_set': True, 'is_statutory': False,
            'is_required_input': True})])
        res = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY', values={},
            documents=['LC_COPY', 'BILL_OF_ENTRY'])
        self.assertEqual(res['status'], 'failed')

    def test_optional_input_missing_is_skipped(self):
        self._active_rule()
        res = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY', values={},
            documents=['LC_COPY', 'BILL_OF_ENTRY'])
        self.assertEqual(res['parameter_results'][0]['result'], 'skipped')
        self.assertTrue(res['passed'])

    def test_invalid_input_value_fails(self):
        self._active_rule()
        res = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY',
            values={'test_limit': 'abc'}, documents=['LC_COPY', 'BILL_OF_ENTRY'])
        self.assertEqual(res['status'], 'failed')

    def test_float_and_date_parameters(self):
        self._active_rule(
            code='TST-TYPES', required_document_type_ids=[(6, 0, [])],
            parameter_ids=[
                (0, 0, {'name': 'Ratio', 'key': 'ratio', 'value_type': 'float', 'operator': 'ge',
                        'value_float': 0.5, 'value_is_set': True, 'is_statutory': False}),
                (0, 0, {'name': 'Cut-off', 'key': 'cutoff', 'value_type': 'date', 'operator': 'le',
                        'value_date': date(2024, 12, 31), 'value_is_set': True, 'is_statutory': False}),
                (0, 0, {'name': 'Flag', 'key': 'flag', 'value_type': 'boolean', 'operator': 'eq',
                        'value_boolean': True, 'value_is_set': True, 'is_statutory': False}),
            ])
        ok = self.engine.evaluate(
            'TST-TYPES', date(2024, 6, 1), 'FOOTWEAR_FACTORY', log=False,
            values={'ratio': 0.75, 'cutoff': '2024-06-30', 'flag': True})
        self.assertTrue(ok['passed'])
        bad = self.engine.evaluate(
            'TST-TYPES', date(2024, 6, 1), 'FOOTWEAR_FACTORY', log=False,
            values={'ratio': 0.25, 'cutoff': date(2025, 1, 1), 'flag': False})
        self.assertFalse(bad['passed'])
        self.assertEqual([p['result'] for p in bad['parameter_results']], ['fail', 'fail', 'fail'])

    def test_no_rule_results(self):
        self._active_rule()
        unknown = self.engine.evaluate('NO-SUCH-RULE', date(2024, 6, 1), log=False)
        self.assertEqual(unknown['status'], 'no_rule')
        self.assertFalse(unknown['passed'])
        wrong_category = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'LEATHER_GOODS_FACTORY', log=False)
        self.assertEqual(wrong_category['status'], 'no_rule')
        too_early = self.engine.evaluate(
            'TST-RULE-1', date(2023, 6, 1), 'FOOTWEAR_FACTORY', log=False)
        self.assertEqual(too_early['status'], 'no_rule')

    def test_unknown_license_category_raises(self):
        with self.assertRaises(UserError):
            self.engine.evaluate('TST-RULE-1', date(2024, 6, 1), 'DOES_NOT_EXIST')

    def test_evaluation_is_logged(self):
        self._active_rule()
        res = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY', values={'test_limit': 3},
            documents=['LC_COPY', 'BILL_OF_ENTRY'], res_model='stock.picking', res_id=42)
        entry = self.env['bond.compliance.evaluation'].browse(res['evaluation_id'])
        self.assertEqual(entry.status, 'passed')
        self.assertEqual(entry.res_model, 'stock.picking')
        self.assertEqual(entry.res_id, 42)
        self.assertEqual(entry.evaluated_on, date(2024, 6, 1))
        self.assertIn('"rule_version": 1', entry.result_json)

    def test_get_parameter_value(self):
        rule = self._active_rule()
        self.assertEqual(rule.get_parameter_value('test_limit'), 10)
        self.assertEqual(rule.get_parameter_value('missing', default='n/a'), 'n/a')

    # --- exceptions ----------------------------------------------------
    def _make_exception(self, rule, **extra):
        vals = {
            'rule_id': rule.id, 'reference': 'GRN-EXC-1',
            'reason': 'Test justification', 'valid_from': date(2024, 1, 1),
            'valid_to': date(2024, 12, 31),
        }
        vals.update(extra)
        return self.env['bond.compliance.exception'].with_user(self.user_officer).create(vals)

    def test_exception_workflow_and_evaluation_coverage(self):
        rule = self._active_rule()
        exc = self._make_exception(rule)
        self.assertTrue(exc.name.startswith('BCE/'))
        exc.with_user(self.user_officer).action_submit()
        exc.with_user(self.user_approver).action_approve()
        self.assertEqual(exc.state, 'approved')
        res = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY', values={'test_limit': 99},
            documents=['LC_COPY', 'BILL_OF_ENTRY'], reference='GRN-EXC-1')
        self.assertEqual(res['status'], 'failed')
        self.assertFalse(res['passed'])
        self.assertTrue(res['covered_by_exception'])
        self.assertEqual(res['exception_ids'], exc.ids)
        other = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY', values={'test_limit': 99},
            documents=['LC_COPY', 'BILL_OF_ENTRY'], reference='GRN-OTHER')
        self.assertFalse(other['covered_by_exception'])

    def test_exception_outside_validity_does_not_apply(self):
        rule = self._active_rule()
        exc = self._make_exception(rule, valid_from=date(2024, 7, 1))
        exc.with_user(self.user_officer).action_submit()
        exc.with_user(self.user_approver).action_approve()
        res = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY', values={'test_limit': 99},
            reference='GRN-EXC-1', log=False)
        self.assertFalse(res['covered_by_exception'])

    def test_exception_requires_time_box(self):
        rule = self._active_rule()
        exc = self._make_exception(rule, valid_to=False)
        with self.assertRaises(UserError):
            exc.with_user(self.user_officer).action_submit()

    def test_exception_requester_cannot_approve(self):
        rule = self._active_rule()
        exc = self.env['bond.compliance.exception'].with_user(self.user_officer_approver).create({
            'rule_id': rule.id, 'reference': 'GRN-EXC-2', 'reason': 'Test',
            'valid_from': date(2024, 1, 1), 'valid_to': date(2024, 12, 31)})
        exc.with_user(self.user_officer_approver).action_submit()
        with self.assertRaises(UserError):
            exc.with_user(self.user_officer_approver).action_approve()

    def test_exception_cannot_be_created_approved_or_edited(self):
        rule = self._active_rule()
        with self.assertRaises(UserError):
            self._make_exception(rule, state='approved')
        exc = self._make_exception(rule)
        exc.with_user(self.user_officer).action_submit()
        with self.assertRaises(UserError):
            exc.with_user(self.user_officer).write({'reason': 'Changed after submission'})

    def test_exception_expiry_cron(self):
        rule = self._active_rule()
        exc = self._make_exception(rule, valid_from=date(2020, 1, 1), valid_to=date(2020, 12, 31))
        exc.with_user(self.user_officer).action_submit()
        exc.with_user(self.user_approver).action_approve()
        self.env['bond.compliance.exception']._cron_expire_exceptions()
        self.assertEqual(exc.state, 'expired')

    def test_exception_requires_active_rule(self):
        draft = self._make_rule(code='TST-NOT-ACTIVE')
        exc = self._make_exception(draft)
        with self.assertRaises(UserError):
            exc.with_user(self.user_officer).action_submit()

    # --- reminders -----------------------------------------------------
    def test_reminder_cron_schedules_activities(self):
        rule = self._active_rule(next_review_date=date(2000, 1, 1))
        self.Rule._cron_compliance_reminders()
        summaries = rule.sudo().activity_ids.mapped('summary')
        self.assertIn('Compliance rule re-verification due', summaries)
