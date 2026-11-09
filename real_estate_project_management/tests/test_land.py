# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install')
class TestRealEstateLand(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner_1 = self.env['res.partner'].create({'name': 'Test Owner One'})
        self.partner_2 = self.env['res.partner'].create({'name': 'Test Owner Two'})
        self.owner_1 = self.env['real.estate.land.owner'].create({
            'partner_id': self.partner_1.id,
            'ownership_type': 'individual',
        })
        self.owner_2 = self.env['real.estate.land.owner'].create({
            'partner_id': self.partner_2.id,
            'ownership_type': 'individual',
        })

    def test_land_sequence_generated(self):
        land = self.env['real.estate.land'].create({
            'land_name': 'Test Land Alpha',
            'area': 5.0,
            'area_uom': 'bigha',
        })
        self.assertTrue(land.name and land.name != 'New',
                         'Land number should be auto-generated from sequence.')
        self.assertTrue(land.name.startswith('LAND-'))

    def test_ownership_must_total_100_before_verify(self):
        land = self.env['real.estate.land'].create({
            'land_name': 'Test Land Beta',
            'area': 3.0,
            'area_uom': 'bigha',
        })
        self.env['real.estate.land.ownership'].create({
            'land_id': land.id,
            'owner_id': self.owner_1.id,
            'ownership_percentage': 60.0,
        })
        land.action_submit_verification()
        with self.assertRaises(ValidationError):
            land.action_verify()

        # complete to 100%
        self.env['real.estate.land.ownership'].create({
            'land_id': land.id,
            'owner_id': self.owner_2.id,
            'ownership_percentage': 40.0,
        })
        land.action_verify()
        self.assertEqual(land.state, 'verified')

    def test_ownership_cannot_exceed_100(self):
        land = self.env['real.estate.land'].create({
            'land_name': 'Test Land Gamma',
            'area': 2.0,
            'area_uom': 'bigha',
        })
        self.env['real.estate.land.ownership'].create({
            'land_id': land.id,
            'owner_id': self.owner_1.id,
            'ownership_percentage': 80.0,
        })
        with self.assertRaises(ValidationError):
            self.env['real.estate.land.ownership'].create({
                'land_id': land.id,
                'owner_id': self.owner_2.id,
                'ownership_percentage': 30.0,
            })

    def test_verify_wrong_state_raises(self):
        land = self.env['real.estate.land'].create({
            'land_name': 'Test Land Delta',
            'area': 1.0,
            'area_uom': 'bigha',
        })
        self.env['real.estate.land.ownership'].create({
            'land_id': land.id,
            'owner_id': self.owner_1.id,
            'ownership_percentage': 100.0,
        })
        # still draft -> cannot verify directly
        with self.assertRaises(UserError):
            land.action_verify()
