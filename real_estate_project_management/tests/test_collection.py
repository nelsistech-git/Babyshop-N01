# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError
from odoo import fields


@tagged('post_install', '-at_install')
class TestRealEstateCollection(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env['real.estate.project'].create({'project_name': 'Collection Test Project'})
        self.building = self.env['real.estate.building'].create({
            'building_name': 'Collection Tower', 'project_id': self.project.id})
        self.floor = self.env['real.estate.floor'].create({
            'floor_name': 'Floor 1', 'floor_number': 1, 'building_id': self.building.id})
        self.unit = self.env['real.estate.unit'].create({
            'name': 'C-101', 'floor_id': self.floor.id,
            'pricing_method': 'fixed', 'fixed_base_price': 12000000,
        })
        self.customer = self.env['res.partner'].create({'name': 'Installment Buyer'})
        self.agreement = self.env['real.estate.sale.agreement'].create({
            'customer_id': self.customer.id,
            'unit_id': self.unit.id,
            'total_price': 12000000,
            'down_payment': 2000000,
            'booking_amount': 1000000,
        })

    def test_financeable_amount_computation(self):
        plan = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
        })
        # 12,000,000 - 2,000,000 - 1,000,000 = 9,000,000
        self.assertEqual(plan.financeable_amount, 9000000.0)

    def test_generate_equal_schedule(self):
        plan = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
            'plan_type': 'equal',
            'frequency': 'monthly',
            'number_of_installments': 9,
            'start_date': '2025-01-01',
        })
        plan.action_generate_schedule()
        self.assertEqual(len(plan.installment_ids), 9)
        # total must exactly match financeable_amount despite rounding
        self.assertAlmostEqual(sum(plan.installment_ids.mapped('amount')),
                                plan.financeable_amount, places=2)
        first = plan.installment_ids.sorted('installment_number')[0]
        second = plan.installment_ids.sorted('installment_number')[1]
        self.assertEqual((second.due_date - first.due_date).days, 31)  # Jan has 31 days

    def test_generate_schedule_twice_blocked(self):
        plan = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
            'number_of_installments': 4,
            'start_date': '2025-01-01',
        })
        plan.action_generate_schedule()
        with self.assertRaises(UserError):
            plan.action_generate_schedule()

    def test_activate_blocked_if_overscheduled(self):
        plan = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
        })
        self.env['real.estate.installment'].create({
            'plan_id': plan.id, 'installment_number': 1,
            'due_date': '2025-01-01', 'amount': 99000000,  # way over
        })
        with self.assertRaises(UserError):
            plan.action_activate()

    def test_single_active_plan_per_agreement(self):
        plan1 = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
        })
        with self.assertRaises(Exception):
            self.env['real.estate.installment.plan'].create({
                'sale_agreement_id': self.agreement.id,
            })

    def test_collection_confirm_updates_installment_paid_amount(self):
        plan = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
            'number_of_installments': 3,
            'start_date': '2025-01-01',
        })
        plan.action_generate_schedule()
        plan.action_activate()
        installment = plan.installment_ids.sorted('installment_number')[0]

        collection = self.env['real.estate.collection'].create({
            'customer_id': self.customer.id,
            'sale_agreement_id': self.agreement.id,
            'installment_id': installment.id,
            'amount': installment.amount,
        })
        collection.action_confirm()
        self.assertEqual(installment.paid_amount, installment.amount)
        self.assertEqual(installment.due_amount, 0.0)
        self.assertEqual(installment.status, 'paid')

    def test_collection_overpayment_blocked(self):
        plan = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
            'number_of_installments': 3,
            'start_date': '2025-01-01',
        })
        plan.action_generate_schedule()
        installment = plan.installment_ids.sorted('installment_number')[0]

        collection = self.env['real.estate.collection'].create({
            'customer_id': self.customer.id,
            'installment_id': installment.id,
            'amount': installment.amount * 2,
        })
        with self.assertRaises(UserError):
            collection.action_confirm()

    def test_collection_overpayment_allowed_with_flag(self):
        plan = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
            'number_of_installments': 3,
            'start_date': '2025-01-01',
        })
        plan.action_generate_schedule()
        installment = plan.installment_ids.sorted('installment_number')[0]

        collection = self.env['real.estate.collection'].create({
            'customer_id': self.customer.id,
            'installment_id': installment.id,
            'amount': installment.amount * 2,
            'allow_overpayment': True,
        })
        collection.action_confirm()
        self.assertEqual(collection.state, 'confirmed')

    def test_cancel_collection_reverts_paid_amount(self):
        plan = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
            'number_of_installments': 3,
            'start_date': '2025-01-01',
        })
        plan.action_generate_schedule()
        installment = plan.installment_ids.sorted('installment_number')[0]
        collection = self.env['real.estate.collection'].create({
            'customer_id': self.customer.id,
            'installment_id': installment.id,
            'amount': installment.amount,
        })
        collection.action_confirm()
        self.assertEqual(installment.status, 'paid')
        collection.action_cancel()
        self.assertEqual(installment.paid_amount, 0.0)
        self.assertNotEqual(installment.status, 'paid')

    def test_status_computation_overdue(self):
        plan = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
        })
        installment = self.env['real.estate.installment'].create({
            'plan_id': plan.id, 'installment_number': 1,
            'due_date': '2020-01-01', 'amount': 100000,
        })
        installment._compute_status_now()
        self.assertEqual(installment.status, 'overdue')

    def test_late_fee_percentage_after_grace_period(self):
        plan = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
            'grace_period_days': 5,
            'late_fee_type': 'percentage',
            'late_fee_value': 2.0,
        })
        installment = self.env['real.estate.installment'].create({
            'plan_id': plan.id, 'installment_number': 1,
            'due_date': '2020-01-01', 'amount': 100000,
        })
        self.assertEqual(installment.late_fee_amount, 2000.0)  # 2% of 100,000

    def test_customer_ledger_totals(self):
        plan = self.env['real.estate.installment.plan'].create({
            'sale_agreement_id': self.agreement.id,
            'number_of_installments': 2,
            'start_date': '2025-01-01',
        })
        plan.action_generate_schedule()
        plan.action_activate()
        first = plan.installment_ids.sorted('installment_number')[0]
        collection = self.env['real.estate.collection'].create({
            'customer_id': self.customer.id,
            'installment_id': first.id,
            'amount': first.amount,
        })
        collection.action_confirm()
        self.assertEqual(self.customer.ledger_total_paid, first.amount)
        self.assertGreater(self.customer.ledger_total_due, 0)
