# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRealEstateDashboard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env['real.estate.project'].create({
            'project_name': 'Dashboard Test Project', 'state': 'construction'})
        self.building = self.env['real.estate.building'].create({
            'building_name': 'Dashboard Tower', 'project_id': self.project.id})
        self.floor = self.env['real.estate.floor'].create({
            'floor_name': 'Floor 1', 'floor_number': 1, 'building_id': self.building.id})
        self.unit_available = self.env['real.estate.unit'].create({
            'name': 'D-101', 'floor_id': self.floor.id,
            'pricing_method': 'fixed', 'fixed_base_price': 5000000, 'status': 'available',
        })
        self.unit_sold = self.env['real.estate.unit'].create({
            'name': 'D-102', 'floor_id': self.floor.id,
            'pricing_method': 'fixed', 'fixed_base_price': 6000000, 'status': 'sold',
        })

    def test_dashboard_unit_kpis(self):
        dashboard = self.env['real.estate.dashboard'].new({})
        self.assertGreaterEqual(dashboard.total_units, 2)
        self.assertGreaterEqual(dashboard.available_units, 1)
        self.assertGreaterEqual(dashboard.sold_units, 1)

    def test_dashboard_project_kpis(self):
        dashboard = self.env['real.estate.dashboard'].new({})
        self.assertGreaterEqual(dashboard.total_projects, 1)
        self.assertGreaterEqual(dashboard.active_projects, 1)

    def test_dashboard_sales_kpi_reflects_agreement(self):
        customer = self.env['res.partner'].create({'name': 'Dashboard Buyer'})
        agreement = self.env['real.estate.sale.agreement'].create({
            'customer_id': customer.id, 'unit_id': self.unit_sold.id, 'total_price': 6000000,
        })
        agreement.action_activate()
        dashboard = self.env['real.estate.dashboard'].new({})
        self.assertGreaterEqual(dashboard.total_sales, 6000000)


@tagged('post_install', '-at_install')
class TestRealEstateProjectProfitability(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env['real.estate.project'].create({'project_name': 'Profitability Test Project'})
        self.building = self.env['real.estate.building'].create({
            'building_name': 'Profit Tower', 'project_id': self.project.id})
        self.floor = self.env['real.estate.floor'].create({
            'floor_name': 'Floor 1', 'floor_number': 1, 'building_id': self.building.id})
        self.unit = self.env['real.estate.unit'].create({
            'name': 'P-101', 'floor_id': self.floor.id,
            'pricing_method': 'fixed', 'fixed_base_price': 10000000,
        })
        self.customer = self.env['res.partner'].create({'name': 'Profitability Buyer'})

    def test_profitability_revenue_and_cost(self):
        agreement = self.env['real.estate.sale.agreement'].create({
            'customer_id': self.customer.id, 'unit_id': self.unit.id, 'total_price': 10000000,
        })
        agreement.action_activate()

        budget = self.env['real.estate.project.budget'].create({'project_id': self.project.id})
        self.env['real.estate.budget.allocation'].create({
            'budget_id': budget.id, 'budget_head': 'construction',
            'allocated_amount': 6000000, 'actual_amount': 4000000,
        })

        self.assertEqual(self.project.total_sales_value, 10000000)
        self.assertEqual(self.project.total_actual_cost, 4000000)
        self.assertEqual(self.project.total_revenue, 10000000)
        self.assertEqual(self.project.gross_profit, 6000000)
        self.assertAlmostEqual(self.project.profit_margin_percentage, 60.0)

    def test_rental_income_included_in_revenue(self):
        tenant = self.env['res.partner'].create({'name': 'Profitability Tenant'})
        rental = self.env['real.estate.rental.agreement'].create({
            'tenant_id': tenant.id, 'unit_id': self.unit.id, 'monthly_rent': 20000,
        })
        rental.action_confirm()
        rental.action_activate()
        collection = self.env['real.estate.collection'].create({
            'customer_id': tenant.id, 'rental_agreement_id': rental.id, 'amount': 20000,
        })
        collection.action_confirm()

        # Phase 10 bug fix: rent collection must resolve project_id/unit_id
        self.assertEqual(collection.project_id, self.project)
        self.assertEqual(collection.unit_id, self.unit)

        self.assertEqual(self.project.rental_income, 20000)
        self.assertEqual(self.project.total_revenue, 20000)
