# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import BondComplianceCommon


@tagged('post_install', '-at_install', 'nelsis_bond_compliance')
class TestRuleVersions(BondComplianceCommon):

    def test_new_version_supersedes_previous(self):
        v1 = self._activate(self._make_rule())
        v2 = self._new_version(v1, date(2025, 1, 1))
        self.assertEqual(v2.version, 2)
        self.assertEqual(v2.previous_version_id, v1)
        self.assertEqual(v2.verification_status, 'draft')
        self.assertEqual(len(v2.parameter_ids), 1)
        self._activate(v2)
        self.assertEqual(v1.verification_status, 'superseded')
        self.assertEqual(v1.effective_to, date(2024, 12, 31))
        self.assertEqual(v2.verification_status, 'active')

    def test_effective_dates_select_the_right_version(self):
        v1 = self._activate(self._make_rule())
        v2 = self._activate(self._new_version(v1, date(2025, 1, 1)))
        get = self.engine.get_applicable_rule
        self.assertEqual(get('TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY').id, v1.id)
        self.assertEqual(get('TST-RULE-1', date(2024, 12, 31), 'FOOTWEAR_FACTORY').id, v1.id)
        self.assertEqual(get('TST-RULE-1', date(2025, 1, 1), 'FOOTWEAR_FACTORY').id, v2.id)
        self.assertFalse(get('TST-RULE-1', date(2023, 12, 31), 'FOOTWEAR_FACTORY'))

    def test_draft_or_unapproved_rules_are_never_applied(self):
        self._make_rule(code='TST-DRAFT')
        approved = self._approve(self._make_rule(code='TST-APPROVED'))
        self.assertEqual(approved.verification_status, 'approved')
        for code in ('TST-DRAFT', 'TST-APPROVED'):
            self.assertFalse(self.engine.get_applicable_rule(code, date(2024, 6, 1), 'FOOTWEAR_FACTORY'))

    def test_new_version_must_start_after_previous(self):
        v1 = self._activate(self._make_rule())
        v2 = self._new_version(v1, date(2024, 1, 1))
        self._approve(v2)
        with self.assertRaises(UserError):
            v2.with_user(self.user_approver).action_activate()
        self.assertEqual(v1.verification_status, 'active')

    def test_only_one_open_new_version(self):
        v1 = self._activate(self._make_rule())
        self._new_version(v1, date(2025, 1, 1))
        with self.assertRaises(UserError):
            v1.with_user(self.user_officer).action_new_version()

    def test_new_version_only_from_active_rule(self):
        draft = self._make_rule()
        with self.assertRaises(UserError):
            draft.with_user(self.user_officer).action_new_version()

    def test_overlapping_versions_are_rejected(self):
        v1 = self._activate(self._make_rule())
        vals = self._rule_vals(effective_from=date(2024, 6, 1), version=2)
        rogue = self.Rule.with_user(self.user_officer).with_context(
            bond_compliance_workflow=True).create(vals)
        self.assertEqual(rogue.version, 2)
        self._approve(rogue)
        with self.assertRaises(ValidationError):
            rogue.with_user(self.user_approver).action_activate()
        self.assertEqual(v1.verification_status, 'active')

    def test_no_overlap_error_for_different_categories(self):
        self._activate(self._make_rule())
        vals = self._rule_vals(
            effective_from=date(2024, 6, 1), version=2,
            applicable_category_ids=[(6, 0, [self.leather_goods.id])])
        other = self.Rule.with_user(self.user_officer).with_context(
            bond_compliance_workflow=True).create(vals)
        self._activate(other)
        self.assertEqual(other.verification_status, 'active')

    def test_historical_evaluation_keeps_rule_version(self):
        v1 = self._activate(self._make_rule())
        before = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY',
            values={'test_limit': 5}, reference='GRN-HIST-1')
        v2 = self._activate(self._new_version(v1, date(2025, 1, 1)))
        entry = self.env['bond.compliance.evaluation'].browse(before['evaluation_id'])
        self.assertEqual(entry.rule_id, v1)
        self.assertEqual(entry.rule_version, 1)
        again = self.engine.evaluate(
            'TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY',
            values={'test_limit': 5}, log=False)
        self.assertEqual(again['rule_id'], v1.id)
        current = self.engine.evaluate(
            'TST-RULE-1', date(2025, 6, 1), 'FOOTWEAR_FACTORY',
            values={'test_limit': 5}, log=False)
        self.assertEqual(current['rule_id'], v2.id)

    def test_evaluation_log_is_immutable(self):
        self._activate(self._make_rule())
        res = self.engine.evaluate('TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY',
                                   values={'test_limit': 5})
        entry = self.env['bond.compliance.evaluation'].browse(res['evaluation_id'])
        with self.assertRaises(UserError):
            entry.write({'status': 'failed'})
        with self.assertRaises(UserError):
            entry.unlink()

    def test_cannot_end_rule_before_a_logged_evaluation(self):
        v1 = self._activate(self._make_rule())
        self.engine.evaluate('TST-RULE-1', date(2024, 6, 1), 'FOOTWEAR_FACTORY',
                             values={'test_limit': 5})
        with self.assertRaises(ValidationError):
            v1.with_user(self.user_approver).write({'effective_to': date(2024, 3, 1)})
        v1.with_user(self.user_approver).write({'effective_to': date(2024, 12, 31)})
        self.assertEqual(v1.effective_to, date(2024, 12, 31))

    def test_end_date_change_requires_approver(self):
        v1 = self._activate(self._make_rule())
        with self.assertRaises(Exception):
            v1.with_user(self.user_officer).write({'effective_to': date(2030, 1, 1)})

    def test_superseded_rule_cannot_be_edited(self):
        v1 = self._activate(self._make_rule())
        self._activate(self._new_version(v1, date(2025, 1, 1)))
        with self.assertRaises(UserError):
            v1.with_user(self.user_approver).write({'effective_to': date(2024, 6, 30)})
        with self.assertRaises(UserError):
            v1.with_user(self.user_officer).write({'name': 'Rewritten history'})
