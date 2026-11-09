# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install')
class TestRealEstateProjectStructure(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env['real.estate.project'].create({
            'project_name': 'Test Project Alpha',
            'project_type': 'apartment',
        })
        self.building = self.env['real.estate.building'].create({
            'building_name': 'Test Tower',
            'name': 'TT-1',
            'project_id': self.project.id,
        })
        self.floor = self.env['real.estate.floor'].create({
            'floor_name': 'Floor 1',
            'floor_number': 1,
            'building_id': self.building.id,
        })

    def test_project_sequence_generated(self):
        self.assertTrue(self.project.name.startswith('PROJ-'))

    def test_project_workflow(self):
        self.assertEqual(self.project.state, 'draft')
        with self.assertRaises(UserError):
            self.project.action_approve()  # cannot skip planning

        self.project.action_start_planning()
        self.assertEqual(self.project.state, 'planning')
        self.project.action_approve()
        self.assertEqual(self.project.state, 'approved')
        self.project.action_start_construction()
        self.assertEqual(self.project.state, 'construction')
        self.project.action_move_to_qc()
        self.project.action_mark_ready()
        self.project.action_complete()
        self.assertEqual(self.project.state, 'completed')
        self.assertTrue(self.project.actual_completion_date)
        self.project.action_close()
        self.assertEqual(self.project.state, 'closed')

    def test_project_date_validation(self):
        with self.assertRaises(ValidationError):
            self.project.write({
                'start_date': '2025-06-01',
                'planned_completion_date': '2025-01-01',
            })

    def test_building_floor_unit_relationship(self):
        unit = self.env['real.estate.unit'].create({
            'name': 'T-101',
            'floor_id': self.floor.id,
            'unit_type': 'apartment',
            'area': 1000,
            'saleable_area': 1000,
            'pricing_method': 'per_sqft',
            'price_per_sqft': 8000,
        })
        # related fields should cascade correctly through the hierarchy
        self.assertEqual(unit.building_id, self.building)
        self.assertEqual(unit.project_id, self.project)
        self.assertIn(unit, self.floor.unit_ids)
        self.assertIn(unit, self.building.unit_ids)
        self.assertIn(unit, self.project.unit_ids)


@tagged('post_install', '-at_install')
class TestRealEstateUnitPricing(TransactionCase):

    def setUp(self):
        super().setUp()
        project = self.env['real.estate.project'].create({'project_name': 'Pricing Test Project'})
        building = self.env['real.estate.building'].create({
            'building_name': 'Pricing Tower', 'project_id': project.id})
        self.floor = self.env['real.estate.floor'].create({
            'floor_name': 'Floor 1', 'floor_number': 1, 'building_id': building.id})

    def test_per_sqft_pricing_computation(self):
        unit = self.env['real.estate.unit'].create({
            'name': 'P-101',
            'floor_id': self.floor.id,
            'pricing_method': 'per_sqft',
            'saleable_area': 1500,
            'price_per_sqft': 8000,
        })
        self.assertEqual(unit.base_price, 1500 * 8000)

    def test_fixed_pricing_computation(self):
        unit = self.env['real.estate.unit'].create({
            'name': 'P-102',
            'floor_id': self.floor.id,
            'pricing_method': 'fixed',
            'fixed_base_price': 12000000,
        })
        self.assertEqual(unit.base_price, 12000000)

    def test_final_price_with_charges_and_discount(self):
        unit = self.env['real.estate.unit'].create({
            'name': 'P-103',
            'floor_id': self.floor.id,
            'pricing_method': 'per_sqft',
            'saleable_area': 1000,
            'price_per_sqft': 8000,
            'discount': 100000,
        })
        self.env['real.estate.unit.charge'].create({
            'unit_id': unit.id, 'charge_type': 'parking', 'amount': 500000,
        })
        self.env['real.estate.unit.charge'].create({
            'unit_id': unit.id, 'charge_type': 'utility', 'amount': 150000,
        })
        # base 8,000,000 + charges 650,000 - discount 100,000
        self.assertEqual(unit.final_price, 8000000 + 650000 - 100000)

    def test_discount_cannot_exceed_price(self):
        with self.assertRaises(ValidationError):
            self.env['real.estate.unit'].create({
                'name': 'P-104',
                'floor_id': self.floor.id,
                'pricing_method': 'per_sqft',
                'saleable_area': 1000,
                'price_per_sqft': 8000,
                'discount': 9000000,
            })

    def test_duplicate_unit_number_in_building_blocked(self):
        self.env['real.estate.unit'].create({
            'name': 'DUP-1', 'floor_id': self.floor.id,
            'pricing_method': 'fixed', 'fixed_base_price': 1000000,
        })
        with self.assertRaises(Exception):
            self.env['real.estate.unit'].create({
                'name': 'DUP-1', 'floor_id': self.floor.id,
                'pricing_method': 'fixed', 'fixed_base_price': 1000000,
            })
