# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install')
class TestRealEstateRental(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env['real.estate.project'].create({'project_name': 'Rental Test Project'})
        self.building = self.env['real.estate.building'].create({
            'building_name': 'Rental Tower', 'project_id': self.project.id})
        self.floor = self.env['real.estate.floor'].create({
            'floor_name': 'Floor 1', 'floor_number': 1, 'building_id': self.building.id})
        self.unit = self.env['real.estate.unit'].create({
            'name': 'R-101', 'floor_id': self.floor.id,
            'pricing_method': 'fixed', 'fixed_base_price': 5000000,
        })
        self.tenant = self.env['res.partner'].create({'name': 'Test Tenant'})

    def _new_rental(self, **overrides):
        vals = {
            'tenant_id': self.tenant.id,
            'unit_id': self.unit.id,
            'monthly_rent': 20000,
            'service_charge': 1000,
        }
        vals.update(overrides)
        return self.env['real.estate.rental.agreement'].create(vals)

    def test_sequence_and_monthly_total(self):
        rental = self._new_rental(utility_charge=500)
        self.assertTrue(rental.name.startswith('RENT-'))
        self.assertEqual(rental.monthly_total, 21500)

    def test_end_date_before_start_date_blocked(self):
        with self.assertRaises(ValidationError):
            self._new_rental(start_date='2025-06-01', end_date='2025-01-01')

    def test_full_workflow_sets_unit_rented(self):
        rental = self._new_rental()
        rental.action_confirm()
        rental.action_activate()
        self.assertEqual(rental.status, 'active')
        self.assertEqual(self.unit.status, 'rented')

    def test_expire_frees_unit(self):
        rental = self._new_rental()
        rental.action_confirm()
        rental.action_activate()
        rental.action_expire()
        self.assertEqual(self.unit.status, 'available')

    def test_rental_blocked_when_unit_already_sold(self):
        agreement = self.env['real.estate.sale.agreement'].create({
            'customer_id': self.tenant.id,
            'unit_id': self.unit.id,
            'total_price': 5000000,
        })
        agreement.action_activate()  # unit -> sold

        rental = self._new_rental()
        rental.action_confirm()
        with self.assertRaises(UserError):
            rental.action_activate()

    def test_sale_blocked_when_unit_already_rented(self):
        rental = self._new_rental()
        rental.action_confirm()
        rental.action_activate()  # unit -> rented

        agreement = self.env['real.estate.sale.agreement'].create({
            'customer_id': self.tenant.id,
            'unit_id': self.unit.id,
            'total_price': 5000000,
        })
        with self.assertRaises(UserError):
            agreement.action_activate()

    def test_generate_rent_schedule(self):
        rental = self._new_rental(start_date='2025-01-01', end_date='2025-03-31', payment_day=5)
        rental.action_generate_rent_schedule()
        self.assertEqual(len(rental.rent_schedule_ids), 3)
        first = rental.rent_schedule_ids.sorted('due_date')[0]
        self.assertEqual(first.due_date.day, 5)
        self.assertEqual(first.amount, rental.monthly_total)

    def test_generate_schedule_twice_blocked(self):
        rental = self._new_rental(start_date='2025-01-01', end_date='2025-02-28')
        rental.action_generate_rent_schedule()
        with self.assertRaises(UserError):
            rental.action_generate_rent_schedule()

    def test_rent_collection_via_shared_model(self):
        rental = self._new_rental(start_date='2025-01-01', end_date='2025-01-31', payment_day=1)
        rental.action_generate_rent_schedule()
        schedule_line = rental.rent_schedule_ids[0]

        collection = self.env['real.estate.collection'].create({
            'customer_id': self.tenant.id,
            'rental_agreement_id': rental.id,
            'rent_schedule_id': schedule_line.id,
            'amount': schedule_line.amount,
        })
        collection.action_confirm()
        self.assertEqual(schedule_line.paid_amount, schedule_line.amount)
        self.assertEqual(schedule_line.status, 'paid')

    def test_rent_overpayment_blocked(self):
        rental = self._new_rental(start_date='2025-01-01', end_date='2025-01-31')
        rental.action_generate_rent_schedule()
        schedule_line = rental.rent_schedule_ids[0]
        collection = self.env['real.estate.collection'].create({
            'customer_id': self.tenant.id,
            'rent_schedule_id': schedule_line.id,
            'amount': schedule_line.amount * 3,
        })
        with self.assertRaises(UserError):
            collection.action_confirm()
