# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install')
class TestRealEstateSales(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env['real.estate.project'].create({'project_name': 'Sales Test Project'})
        self.building = self.env['real.estate.building'].create({
            'building_name': 'Sales Tower', 'project_id': self.project.id})
        self.floor = self.env['real.estate.floor'].create({
            'floor_name': 'Floor 1', 'floor_number': 1, 'building_id': self.building.id})
        self.unit = self.env['real.estate.unit'].create({
            'name': 'S-101', 'floor_id': self.floor.id,
            'pricing_method': 'fixed', 'fixed_base_price': 10000000,
        })
        self.customer = self.env['res.partner'].create({'name': 'Test Buyer'})

    def _new_booking(self, **overrides):
        vals = {
            'customer_id': self.customer.id,
            'unit_id': self.unit.id,
            'sale_price': 10000000,
        }
        vals.update(overrides)
        return self.env['real.estate.booking'].create(vals)

    def test_booking_sequence_and_final_price(self):
        booking = self._new_booking(additional_charges=200000, discount=50000)
        self.assertTrue(booking.name.startswith('BOOK-'))
        self.assertEqual(booking.final_price, 10000000 + 200000 - 50000)

    def test_booking_full_workflow_sets_unit_booked(self):
        booking = self._new_booking()
        self.assertEqual(booking.state, 'draft')
        booking.action_submit()
        booking.action_approve()
        booking.action_confirm()
        self.assertEqual(booking.state, 'confirmed')
        self.assertEqual(self.unit.status, 'booked')

    def test_second_booking_blocked_while_first_confirmed(self):
        booking1 = self._new_booking()
        booking1.action_submit()
        booking1.action_approve()
        booking1.action_confirm()

        customer2 = self.env['res.partner'].create({'name': 'Second Buyer'})
        booking2 = self._new_booking(customer_id=customer2.id)
        booking2.action_submit()
        booking2.action_approve()
        with self.assertRaises(UserError):
            booking2.action_confirm()

    def test_cancel_booking_frees_unit(self):
        booking = self._new_booking()
        booking.action_submit()
        booking.action_approve()
        booking.action_confirm()
        self.assertEqual(self.unit.status, 'booked')
        booking.action_cancel()
        self.assertEqual(self.unit.status, 'available')

    def test_sale_agreement_activation_sets_unit_sold(self):
        booking = self._new_booking()
        booking.action_submit()
        booking.action_approve()
        booking.action_confirm()

        agreement = self.env['real.estate.sale.agreement'].create({
            'customer_id': self.customer.id,
            'unit_id': self.unit.id,
            'booking_id': booking.id,
            'total_price': 10000000,
            'down_payment': 1000000,
        })
        agreement.action_activate()
        self.assertEqual(agreement.state, 'active')
        self.assertEqual(self.unit.status, 'sold')

    def test_agreement_blocked_when_unit_already_has_active_agreement(self):
        agreement1 = self.env['real.estate.sale.agreement'].create({
            'customer_id': self.customer.id,
            'unit_id': self.unit.id,
            'total_price': 10000000,
        })
        agreement1.action_activate()

        customer2 = self.env['res.partner'].create({'name': 'Rival Buyer'})
        agreement2 = self.env['real.estate.sale.agreement'].create({
            'customer_id': customer2.id,
            'unit_id': self.unit.id,
            'total_price': 9500000,
        })
        with self.assertRaises(UserError):
            agreement2.action_activate()

    def test_down_payment_cannot_exceed_total_price(self):
        with self.assertRaises(ValidationError):
            self.env['real.estate.sale.agreement'].create({
                'customer_id': self.customer.id,
                'unit_id': self.unit.id,
                'total_price': 5000000,
                'down_payment': 6000000,
            })

    def test_partner_becomes_real_estate_customer(self):
        self.assertFalse(self.customer.is_real_estate_customer)
        self._new_booking()
        self.assertTrue(self.customer.is_real_estate_customer)
        self.assertEqual(self.customer.booking_count, 1)
