# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError


@tagged('post_install', '-at_install')
class TestRealEstatePortalDashboard(TransactionCase):

    def setUp(self):
        super().setUp()
        P = self.env['res.partner']
        self.p1 = P.create({'name': 'Dash Customer One'})
        self.p2 = P.create({'name': 'Dash Customer Two'})
        self.agent_partner = P.create({'name': 'Dash Agent', 'is_agent': True})
        group_c = self.env.ref('real_estate_project_management.group_real_estate_customer_portal')
        group_a = self.env.ref('real_estate_project_management.group_real_estate_agent')
        base_user = self.env.ref('base.group_user')
        Users = self.env['res.users'].with_context(no_reset_password=True)
        self.u1 = Users.create({'login': 'dash_c1', 'partner_id': self.p1.id,
                                'groups_id': [(6, 0, [base_user.id, group_c.id])]})
        self.u_agent = Users.create({'login': 'dash_ag', 'partner_id': self.agent_partner.id,
                                     'groups_id': [(6, 0, [base_user.id, group_a.id])]})
        project = self.env['real.estate.project'].create({'project_name': 'Dash Project'})
        building = self.env['real.estate.building'].create(
            {'building_name': 'T', 'project_id': project.id})
        floor = self.env['real.estate.floor'].create(
            {'floor_name': 'F1', 'floor_number': 1, 'building_id': building.id})
        unit = self.env['real.estate.unit'].create(
            {'name': 'D-1', 'floor_id': floor.id, 'pricing_method': 'fixed', 'fixed_base_price': 100000})
        self.agreement = self.env['real.estate.sale.agreement'].create({
            'customer_id': self.p1.id, 'unit_id': unit.id, 'total_price': 100000,
            'agent_id': self.agent_partner.id})
        self.agreement.action_activate()
        self.env['real.estate.collection'].create({
            'customer_id': self.p1.id, 'sale_agreement_id': self.agreement.id,
            'amount': 30000, 'state': 'confirmed'})

    def _dash(self, user, role):
        return self.env['real.estate.portal.dashboard'].with_user(user).browse(
            self.env['real.estate.portal.dashboard'].with_user(user)
            .action_open_dashboard(role)['res_id'])

    def test_customer_sees_own_numbers(self):
        dash = self._dash(self.u1, 'customer')
        self.assertEqual(dash.properties_count, 1)
        self.assertAlmostEqual(dash.total_value, 100000)
        self.assertAlmostEqual(dash.total_paid, 30000)
        self.assertAlmostEqual(dash.total_due, 70000)

    def test_other_customer_sees_nothing(self):
        Users = self.env['res.users'].with_context(no_reset_password=True)
        group_c = self.env.ref('real_estate_project_management.group_real_estate_customer_portal')
        u2 = Users.create({'login': 'dash_c2', 'partner_id': self.p2.id,
                           'groups_id': [(6, 0, [self.env.ref('base.group_user').id, group_c.id])]})
        dash = self._dash(u2, 'customer')
        self.assertEqual(dash.properties_count, 0)
        self.assertEqual(dash.total_value, 0)

    def test_agent_dashboard(self):
        dash = self._dash(self.u_agent, 'agent')
        self.assertEqual(dash.sales_count, 1)
        self.assertEqual(dash.customers_count, 1)
        self.assertEqual(dash.commission_count, 1)

    def test_customer_cannot_open_agent_dashboard(self):
        with self.assertRaises(AccessError):
            self.env['real.estate.portal.dashboard'].with_user(self.u1).action_open_dashboard('agent')

    def test_customer_cannot_read_company_sales(self):
        with self.assertRaises(AccessError):
            self.env['real.estate.sale.agreement'].with_user(self.u1).search([])
