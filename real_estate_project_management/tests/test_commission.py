# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestRealEstateCommission(TransactionCase):
    """2-layer commission: Level 1 = seller, Level 2 = whoever referred the seller."""

    def setUp(self):
        super().setUp()
        self.env['real.estate.commission.rule'].search([]).write({'active': False})
        Rule = self.env['real.estate.commission.rule']
        Rule.create({'level': '1', 'calc_type': 'percentage', 'value': 2.0})
        Rule.create({'level': '2', 'calc_type': 'fixed', 'value': 5000.0})
        self.project = self.env['real.estate.project'].create({'project_name': 'Commission Project'})
        building = self.env['real.estate.building'].create(
            {'building_name': 'Tower', 'project_id': self.project.id})
        floor = self.env['real.estate.floor'].create(
            {'floor_name': 'F1', 'floor_number': 1, 'building_id': building.id})
        self.units = self.env['real.estate.unit'].create([
            {'name': 'C-101', 'floor_id': floor.id, 'pricing_method': 'fixed', 'fixed_base_price': 100000},
            {'name': 'C-102', 'floor_id': floor.id, 'pricing_method': 'fixed', 'fixed_base_price': 200000},
        ])
        P = self.env['res.partner']
        self.agent = P.create({'name': 'Agent A', 'is_agent': True})
        self.cust_b = P.create({'name': 'Customer B'})
        self.cust_c = P.create({'name': 'Customer C'})

    def _sell(self, unit, buyer, seller):
        agr = self.env['real.estate.sale.agreement'].create({
            'customer_id': buyer.id, 'unit_id': unit.id, 'total_price': unit.final_price,
            'agent_id': seller.id})
        agr.action_activate()
        return agr

    def test_agent_sale_gets_level1_only(self):
        agr = self._sell(self.units[0], self.cust_b, self.agent)
        self.assertEqual(len(agr.commission_ids), 1)
        com = agr.commission_ids
        self.assertEqual(com.level, '1')
        self.assertEqual(com.beneficiary_id, self.agent)
        self.assertAlmostEqual(com.amount, 2000.0)
        # buyer is now the agent's customer
        self.assertEqual(self.cust_b.referred_by_id, self.agent)

    def test_customer_resale_pays_two_layers(self):
        self._sell(self.units[0], self.cust_b, self.agent)       # A brings B
        agr = self._sell(self.units[1], self.cust_c, self.cust_b)  # B sells to C
        by_level = {c.level: c for c in agr.commission_ids}
        self.assertEqual(by_level['1'].beneficiary_id, self.cust_b)
        self.assertAlmostEqual(by_level['1'].amount, 4000.0)       # 2% of 200000
        self.assertEqual(by_level['2'].beneficiary_id, self.agent)
        self.assertAlmostEqual(by_level['2'].amount, 5000.0)       # fixed

    def test_project_rule_overrides_global(self):
        self.env['real.estate.commission.rule'].create({
            'level': '1', 'calc_type': 'fixed', 'value': 1234.0, 'project_id': self.project.id})
        agr = self._sell(self.units[0], self.cust_b, self.agent)
        self.assertAlmostEqual(agr.commission_ids.amount, 1234.0)

    def test_workflow_and_cancel(self):
        agr = self._sell(self.units[0], self.cust_b, self.agent)
        com = agr.commission_ids
        com.action_approve()
        self.assertEqual(com.state, 'approved')
        agr.action_cancel()
        self.assertEqual(com.state, 'cancelled')

    def test_referral_cycle_blocked(self):
        self.cust_b.referred_by_id = self.agent
        with self.assertRaises(ValidationError):
            self.agent.referred_by_id = self.cust_b

    def test_seller_cannot_be_buyer(self):
        with self.assertRaises(ValidationError):
            self.env['real.estate.sale.agreement'].create({
                'customer_id': self.cust_b.id, 'unit_id': self.units[0].id,
                'total_price': 1000, 'agent_id': self.cust_b.id})
