# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
from datetime import date

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import BondComplianceCommon


@tagged('post_install', '-at_install', 'nelsis_bond_compliance')
class TestRuleLifecycle(BondComplianceCommon):

    # --- workflow and permissions -------------------------------------
    def test_full_workflow_activates_rule(self):
        rule = self._make_rule()
        self.assertEqual(rule.verification_status, 'draft')
        self._activate(rule)
        self.assertEqual(rule.verification_status, 'active')
        self.assertEqual(rule.reviewed_by, self.user_reviewer)
        self.assertEqual(rule.approved_by, self.user_approver)
        self.assertTrue(rule.approved_date)

    def test_rule_cannot_be_created_active(self):
        with self.assertRaises(UserError):
            self._make_rule(verification_status='active')

    def test_workflow_fields_cannot_be_written_directly(self):
        rule = self._make_rule()
        with self.assertRaises(UserError):
            rule.write({'verification_status': 'active'})
        with self.assertRaises(UserError):
            rule.write({'approved_by': self.user_approver.id})

    def test_activation_requires_approver_role(self):
        rule = self._approve(self._make_rule())
        with self.assertRaises(AccessError):
            rule.with_user(self.user_officer).action_activate()
        with self.assertRaises(AccessError):
            rule.with_user(self.user_reviewer).action_activate()
        self.assertEqual(rule.verification_status, 'approved')

    def test_role_restrictions(self):
        rule = self._make_rule()
        with self.assertRaises(AccessError):
            rule.with_user(self.user_reviewer).action_submit_review()
        rule.with_user(self.user_officer).action_submit_review()
        with self.assertRaises(AccessError):
            rule.with_user(self.user_approver).action_mark_reviewed()
        rule.with_user(self.user_reviewer).action_mark_reviewed()
        with self.assertRaises(AccessError):
            rule.with_user(self.user_officer).action_approve()

    def test_read_only_user_cannot_create(self):
        with self.assertRaises(AccessError):
            self._make_rule(user=self.user_reader)

    def test_cannot_skip_workflow_steps(self):
        rule = self._make_rule()
        with self.assertRaises(UserError):
            rule.with_user(self.user_approver).action_approve()
        with self.assertRaises(UserError):
            rule.with_user(self.user_approver).action_activate()

    def test_segregation_of_duties(self):
        rule = self._make_rule(user=self.user_officer_reviewer)
        rule.with_user(self.user_officer_reviewer).action_submit_review()
        with self.assertRaises(UserError):
            rule.with_user(self.user_officer_reviewer).action_mark_reviewed()

    def test_approver_must_differ_from_reviewer(self):
        rule = self._make_rule()
        rule.with_user(self.user_officer).action_submit_review()
        rule.with_user(self.user_reviewer).action_mark_reviewed()
        both = self._create_user('bc_rev_app', ['reviewer', 'approver'])
        rule2 = self._make_rule(code='TST-RULE-2')
        rule2.with_user(self.user_officer).action_submit_review()
        rule2.with_user(both).action_mark_reviewed()
        with self.assertRaises(UserError):
            rule2.with_user(both).action_approve()

    def test_reject_and_return_to_draft(self):
        rule = self._make_rule()
        rule.with_user(self.user_officer).action_submit_review()
        with self.assertRaises(UserError):
            rule.with_user(self.user_reviewer).action_reject(reason='  ')
        rule.with_user(self.user_reviewer).action_reject(reason='Wrong SRO number')
        self.assertEqual(rule.verification_status, 'rejected')
        rule.with_user(self.user_officer).action_return_to_draft()
        self.assertEqual(rule.verification_status, 'draft')
        self.assertFalse(rule.rejection_reason)

    # --- professional verification ------------------------------------
    def test_unresolved_legal_interpretation_blocks_approval(self):
        rule = self._make_rule(
            requires_professional_verification=True,
            professional_verification_note='Applicability to leather goods unclear.')
        rule.with_user(self.user_officer).action_submit_review()
        rule.with_user(self.user_reviewer).action_mark_reviewed()
        with self.assertRaises(UserError):
            rule.with_user(self.user_approver).action_approve()
        rule.with_user(self.user_reviewer).write({
            'professional_verified_by': 'Test Customs Consultant',
            'professional_verified_date': date(2024, 1, 5),
        })
        rule.with_user(self.user_approver).action_approve()
        self.assertEqual(rule.verification_status, 'approved')

    # --- immutability --------------------------------------------------
    def test_content_locked_after_submission(self):
        rule = self._make_rule()
        rule.with_user(self.user_officer).action_submit_review()
        with self.assertRaises(UserError):
            rule.with_user(self.user_officer).write({'name': 'Changed'})
        with self.assertRaises(UserError):
            rule.parameter_ids.with_user(self.user_officer).write({'value_integer': 99})
        with self.assertRaises(UserError):
            rule.parameter_ids.with_user(self.user_officer).unlink()

    def test_reviewer_cannot_edit_rule_content(self):
        rule = self._make_rule()
        with self.assertRaises(UserError):
            rule.with_user(self.user_reviewer).write({'name': 'Changed'})

    def test_active_rule_cannot_be_deleted_or_archived(self):
        rule = self._activate(self._make_rule())
        with self.assertRaises(UserError):
            rule.with_user(self.user_officer).unlink()
        with self.assertRaises(UserError):
            rule.with_user(self.user_officer).write({'active': False})

    def test_rule_cannot_be_duplicated(self):
        rule = self._make_rule()
        with self.assertRaises(UserError):
            rule.with_user(self.user_officer).copy()

    # --- invalid configurations ---------------------------------------
    def test_invalid_effective_dates(self):
        with self.assertRaises(ValidationError):
            self._make_rule(effective_to=date(2023, 1, 1))

    def test_invalid_code_format(self):
        with self.assertRaises(ValidationError):
            self._make_rule(code='bad code!')

    def test_code_is_normalised_to_upper_case(self):
        rule = self._make_rule(code='  lower-case-1 ')
        self.assertEqual(rule.code, 'LOWER-CASE-1')

    def test_invalid_source_url(self):
        with self.assertRaises(ValidationError):
            self._make_rule(source_url='not a url')

    def test_submit_requires_official_reference(self):
        rule = self._make_rule(official_reference=False)
        with self.assertRaises(UserError):
            rule.with_user(self.user_officer).action_submit_review()

    def test_submit_requires_explicit_license_category(self):
        rule = self._make_rule(applicable_category_ids=[(6, 0, [])])
        with self.assertRaises(UserError):
            rule.with_user(self.user_officer).action_submit_review()

    def test_submit_requires_effective_from(self):
        rule = self._make_rule(effective_from=False)
        with self.assertRaises(UserError):
            rule.with_user(self.user_officer).action_submit_review()

    def test_statutory_parameter_needs_value_and_source(self):
        def param(**kw):
            vals = {'name': 'Stat', 'key': 'stat_value', 'value_type': 'integer',
                    'operator': 'le', 'is_statutory': True}
            vals.update(kw)
            return [(0, 0, vals)]
        no_value = self._make_rule(code='TST-STAT-1', parameter_ids=param())
        with self.assertRaises(UserError):
            no_value.with_user(self.user_officer).action_submit_review()
        no_source = self._make_rule(
            code='TST-STAT-2', parameter_ids=param(value_integer=5, value_is_set=True))
        with self.assertRaises(UserError):
            no_source.with_user(self.user_officer).action_submit_review()
        ok = self._make_rule(code='TST-STAT-3', parameter_ids=param(
            value_integer=5, value_is_set=True, source_note='Test clause (placeholder)'))
        ok.with_user(self.user_officer).action_submit_review()
        self.assertEqual(ok.verification_status, 'under_review')

    def test_professional_verification_needs_description(self):
        rule = self._make_rule(requires_professional_verification=True)
        with self.assertRaises(UserError):
            rule.with_user(self.user_officer).action_submit_review()

    def test_invalid_parameter_configuration(self):
        rule = self._make_rule()
        Param = self.env['bond.compliance.rule.parameter'].with_user(self.user_officer)
        with self.assertRaises(ValidationError):
            Param.create({'rule_id': rule.id, 'name': 'X', 'key': 'Bad Key'})
        with self.assertRaises(ValidationError):
            Param.create({'rule_id': rule.id, 'name': 'Dup', 'key': 'test_limit'})
        with self.assertRaises(ValidationError):
            Param.create({'rule_id': rule.id, 'name': 'Txt', 'key': 'txt',
                          'value_type': 'char', 'operator': 'lt'})
