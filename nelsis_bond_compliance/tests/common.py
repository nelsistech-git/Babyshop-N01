# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
"""Shared fixtures. All values are NON-STATUTORY test data."""
from datetime import date

from odoo.tests.common import TransactionCase


class BondComplianceCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rule = cls.env['bond.compliance.rule']
        cls.engine = cls.env['bond.compliance.engine']
        cls.user_officer = cls._create_user('bc_officer', ['officer'])
        cls.user_reviewer = cls._create_user('bc_reviewer', ['reviewer'])
        cls.user_approver = cls._create_user('bc_approver', ['approver'])
        cls.user_reader = cls._create_user('bc_reader', [])
        cls.user_officer_reviewer = cls._create_user('bc_off_rev', ['officer', 'reviewer'])
        cls.user_officer_approver = cls._create_user('bc_off_app', ['officer', 'approver'])
        ref = cls.env.ref
        cls.category = ref('nelsis_bond_compliance.bond_rule_category_storage_period')
        cls.footwear = ref('nelsis_bond_compliance.bond_license_category_footwear')
        cls.leather_goods = ref('nelsis_bond_compliance.bond_license_category_leather_goods')
        cls.doc_lc = ref('nelsis_bond_compliance.bond_doc_type_lc_copy')
        cls.doc_boe = ref('nelsis_bond_compliance.bond_doc_type_bill_of_entry')

    @classmethod
    def _create_user(cls, login, roles):
        xmlids = ['base.group_user', 'nelsis_bond_compliance.group_bond_compliance_user']
        xmlids += ['nelsis_bond_compliance.group_bond_compliance_%s' % role for role in roles]
        return cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': login,
            'login': login,
            'email': '%s@example.com' % login,
            'groups_id': [(6, 0, [cls.env.ref(x).id for x in xmlids])],
        })

    def _rule_vals(self, code='TST-RULE-1', effective_from=date(2024, 1, 1), **extra):
        vals = {
            'name': 'Test rule',
            'code': code,
            'rule_category_id': self.category.id,
            'official_reference': 'TEST-REF-PLACEHOLDER',
            'source_url': 'https://nbr.gov.bd/test-placeholder',
            'publication_date': date(2023, 12, 1),
            'effective_from': effective_from,
            'description': 'Non-statutory test rule.',
            'applicable_category_ids': [(6, 0, [self.footwear.id])],
            'parameter_ids': [(0, 0, {
                'name': 'Test limit', 'key': 'test_limit', 'value_type': 'integer',
                'operator': 'le', 'value_integer': 10, 'value_is_set': True,
                'is_statutory': False,
            })],
        }
        vals.update(extra)
        return vals

    def _make_rule(self, user=None, **kwargs):
        user = user or self.user_officer
        return self.Rule.with_user(user).create(self._rule_vals(**kwargs))

    def _approve(self, rule):
        rule.with_user(self.user_officer).action_submit_review()
        rule.with_user(self.user_reviewer).action_mark_reviewed()
        rule.with_user(self.user_approver).action_approve()
        return rule

    def _activate(self, rule):
        self._approve(rule)
        rule.with_user(self.user_approver).action_activate()
        return rule

    def _new_version(self, rule, effective_from, **extra):
        action = rule.with_user(self.user_officer).action_new_version()
        new_rule = self.Rule.browse(action['res_id'])
        vals = {
            'official_reference': 'TEST-REF-V%s' % new_rule.version,
            'source_url': 'https://nbr.gov.bd/test-placeholder-v%s' % new_rule.version,
            'effective_from': effective_from,
        }
        vals.update(extra)
        new_rule.with_user(self.user_officer).write(vals)
        return new_rule
