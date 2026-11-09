# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install')
class TestRealEstateLandAgreement(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Agreement Test Owner'})
        self.owner = self.env['real.estate.land.owner'].create({
            'partner_id': self.partner.id,
            'ownership_type': 'individual',
        })
        self.land = self.env['real.estate.land'].create({
            'land_name': 'Agreement Test Land',
            'area': 4.0,
            'area_uom': 'bigha',
        })
        self.env['real.estate.land.ownership'].create({
            'land_id': self.land.id,
            'owner_id': self.owner.id,
            'ownership_percentage': 100.0,
        })

    def _new_agreement(self, **overrides):
        vals = {
            'agreement_type': 'joint_venture',
            'land_id': self.land.id,
            'land_owner_ids': [(6, 0, [self.owner.id])],
            'developer_share_percentage': 70.0,
            'land_owner_share_percentage': 30.0,
        }
        vals.update(overrides)
        return self.env['real.estate.land.agreement'].create(vals)

    def test_sequence_generated(self):
        agreement = self._new_agreement()
        self.assertTrue(agreement.name.startswith('AGR-'))

    def test_end_date_before_start_date_raises(self):
        with self.assertRaises(ValidationError):
            self._new_agreement(
                start_date='2025-06-01',
                end_date='2025-01-01',
            )

    def test_shares_exceeding_100_raises(self):
        with self.assertRaises(ValidationError):
            self._new_agreement(
                developer_share_percentage=80.0,
                land_owner_share_percentage=30.0,
            )

    def test_full_approval_workflow(self):
        agreement = self._new_agreement()
        self.assertEqual(agreement.state, 'draft')

        # cannot skip straight to approve
        with self.assertRaises(UserError):
            agreement.action_approve()

        agreement.action_submit_legal_review()
        self.assertEqual(agreement.state, 'legal_review')

        agreement.action_submit_management_review()
        self.assertEqual(agreement.state, 'management_review')

        # approve requires Director/Administrator group; admin user in tests
        # normally has full access via superuser context
        agreement.action_approve()
        self.assertEqual(agreement.state, 'approved')

        agreement.action_activate()
        self.assertEqual(agreement.state, 'active')
        self.assertEqual(self.land.state, 'under_agreement')

        agreement.action_expire()
        self.assertEqual(agreement.state, 'expired')
