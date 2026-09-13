# -*- coding: utf-8 -*-
"""Shared fixtures for the Grameen Cybernet ERM test suite (SRS 89 / 90)."""

from odoo import fields
from odoo.tests.common import TransactionCase


class GcErmCommon(TransactionCase):
    """Builds a complete, realistic ERM environment once per test class."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company

        # ------------------------------------------------------------------
        # Users, one per SRS role (SRS 7)
        # ------------------------------------------------------------------
        cls.group_sales = cls.env.ref('gc_erm_lead_to_billing.group_gc_sales_user')
        cls.group_hod = cls.env.ref('gc_erm_lead_to_billing.group_gc_sales_hod')
        cls.group_tech = cls.env.ref('gc_erm_lead_to_billing.group_gc_technical_user')
        cls.group_tech_mgr = cls.env.ref(
            'gc_erm_lead_to_billing.group_gc_technical_manager')
        cls.group_impl = cls.env.ref(
            'gc_erm_lead_to_billing.group_gc_implementation_user')
        cls.group_inventory = cls.env.ref(
            'gc_erm_lead_to_billing.group_gc_inventory_user')
        cls.group_purchase = cls.env.ref(
            'gc_erm_lead_to_billing.group_gc_purchase_user')
        cls.group_accounts = cls.env.ref(
            'gc_erm_lead_to_billing.group_gc_accounts_user')
        cls.group_admin = cls.env.ref('gc_erm_lead_to_billing.group_gc_erm_admin')

        cls.user_sales = cls._create_user('gc_sales', 'Sam Sales', cls.group_sales)
        cls.user_hod = cls._create_user('gc_hod', 'Hana HOD', cls.group_hod)
        cls.user_engineer = cls._create_user('gc_eng', 'Eva Engineer', cls.group_tech)
        cls.user_tech_mgr = cls._create_user(
            'gc_tmgr', 'Tom TechManager', cls.group_tech_mgr)
        cls.user_impl = cls._create_user('gc_impl', 'Ian Implementer', cls.group_impl)
        cls.user_purchase = cls._create_user(
            'gc_buyer', 'Pia Purchaser', cls.group_purchase)
        cls.user_accounts = cls._create_user(
            'gc_acct', 'Anna Accounts', cls.group_accounts)
        cls.user_admin = cls._create_user('gc_admin', 'Adam Admin', cls.group_admin)

        # ------------------------------------------------------------------
        # Master data
        # ------------------------------------------------------------------
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer Ltd',
            'is_company': True,
            'email': 'customer@test.example.com',
            'phone': '+8801700000000',
            'gc_district': 'Dhaka',
            'gc_area': 'Gulshan',
            'gc_customer_type': 'corporate',
        })
        cls.contact = cls.env['res.partner'].create({
            'name': 'Mr Contact',
            'parent_id': cls.partner.id,
            'function': 'IT Manager',
            'email': 'contact@test.example.com',
        })
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor Ltd', 'supplier_rank': 1,
        })

        cls.product_router = cls.env['product.product'].create({
            'name': 'Test Router', 'type': 'product',
            'standard_price': 40000.0, 'list_price': 55000.0,
            'sale_ok': True, 'purchase_ok': True,
        })
        cls.product_fiber = cls.env['product.product'].create({
            'name': 'Test Fiber Cable', 'type': 'product',
            'standard_price': 30.0, 'list_price': 45.0,
            'sale_ok': True, 'purchase_ok': True,
        })
        cls.product_service = cls.env['product.product'].create({
            'name': 'Test Installation Service', 'type': 'service',
            'standard_price': 5000.0, 'list_price': 8000.0,
            'sale_ok': True, 'invoice_policy': 'order',
        })

        cls.service = cls.env.ref('gc_erm_lead_to_billing.gc_service_internet')
        cls.service.product_id = cls.product_service

        cls.team_tech = cls.env['gc.erm.team'].create({
            'name': 'Test Technical Team', 'code': 'TT1',
            'team_type': 'technical', 'leader_id': cls.user_engineer.id,
            'member_ids': [(6, 0, (cls.user_engineer | cls.user_tech_mgr).ids)],
        })
        cls.team_impl = cls.env['gc.erm.team'].create({
            'name': 'Test Implementation Team', 'code': 'TI1',
            'team_type': 'implementation', 'leader_id': cls.user_impl.id,
            'member_ids': [(6, 0, cls.user_impl.ids)],
        })
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.company.id)], limit=1)

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------
    @classmethod
    def _create_user(cls, login, name, group):
        return cls.env['res.users'].create({
            'name': name,
            'login': login,
            'email': '%s@test.example.com' % login,
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, (group | cls.env.ref('base.group_user')).ids)],
        })

    @classmethod
    def _stock_in(cls, product, qty):
        """Put ``qty`` of ``product`` into the main stock location."""
        cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'location_id': cls.warehouse.lot_stock_id.id,
            'inventory_quantity': qty,
        })._apply_inventory()

    def _create_lead(self, user=None, **overrides):
        env = self.env(user=user) if user else self.env
        vals = {
            'partner_id': self.partner.id,
            'contact_id': self.contact.id,
            'salesperson_id': (user or self.env.user).id,
            'description': '<p>10 Mbps dedicated internet link</p>',
            'expected_revenue': 250000.0,
            'district': 'Dhaka',
            'area': 'Gulshan',
            'gps_latitude': 23.7925,
            'gps_longitude': 90.4078,
            'service_line_ids': [(0, 0, {
                'service_id': self.service.id,
                'quantity': 1.0,
                'bandwidth': '10 Mbps',
            })],
        }
        vals.update(overrides)
        return env['gc.erm.lead'].create(vals)

    def _approved_lead(self):
        lead = self._create_lead(user=self.user_sales)
        lead.with_user(self.user_sales).action_submit()
        lead.with_user(self.user_hod).action_approve()
        return lead

    def _completed_survey(self, lead=None):
        lead = lead or self._approved_lead()
        action = lead.with_user(self.user_sales).action_create_survey()
        survey = self.env['gc.erm.survey'].browse(action['res_id'])
        self.env['gc.erm.survey.assign.wizard'].with_user(self.user_sales).create({
            'survey_id': survey.id,
            'team_id': self.team_tech.id,
            'engineer_id': self.user_engineer.id,
            'survey_date': fields.Date.today(),
            'deadline': fields.Date.add(fields.Date.today(), days=2),
            'priority': '1',
        }).action_assign()
        survey.with_user(self.user_engineer).action_start()
        survey.with_user(self.user_engineer).write({
            'feasibility': 'feasible',
            'network_availability': 'yes',
            'fiber_availability': 'yes',
            'power_availability': 'yes',
            'technical_remarks': 'POP within 300 m, fibre available.',
        })
        return survey

    def _boq_for(self, survey, margin_method='cost_pct', margin_value=25.0):
        action = survey.with_user(self.user_engineer).action_create_boq()
        boq = self.env['gc.erm.boq'].browse(action['res_id'])
        boq.with_user(self.user_engineer).write({
            'margin_method': margin_method,
            'margin_value': margin_value,
            'line_ids': [
                (0, 0, {
                    'product_id': self.product_router.id,
                    'name': 'Router', 'quantity': 1.0, 'unit_cost': 40000.0,
                    'installation_cost': 3000.0, 'transport_cost': 1000.0,
                    'other_cost': 500.0,
                }),
                (0, 0, {
                    'product_id': self.product_fiber.id,
                    'name': 'Fiber', 'quantity': 300.0, 'unit_cost': 30.0,
                    'transport_cost': 2000.0,
                }),
            ],
        })
        return boq

    def _submitted_technical_report(self, survey=None, boq=None):
        survey = survey or self._completed_survey()
        boq = boq or self._boq_for(survey)
        boq.with_user(self.user_engineer).action_confirm()
        survey.with_user(self.user_engineer).action_complete()
        action = survey.with_user(self.user_engineer).action_create_technical_report()
        report = self.env['gc.erm.technical.report'].browse(action['res_id'])
        report.with_user(self.user_engineer).write({
            'boq_id': boq.id,
            'feasibility': 'feasible',
            'implementation_timeline': '10 working days',
        })
        report.with_user(self.user_engineer).action_submit()
        return report

    def _approved_proposal(self, report=None):
        report = report or self._submitted_technical_report()
        action = report.with_user(self.user_sales).action_create_proposal()
        proposal = self.env['gc.erm.proposal'].browse(action['res_id'])
        proposal.with_user(self.user_sales).action_submit()
        proposal.with_user(self.user_hod).action_approve()
        return proposal

    def _confirmed_work_order(self, proposal=None):
        proposal = proposal or self._approved_proposal()
        wizard = self.env['gc.erm.acceptance.wizard'].with_user(
            self.user_sales).create({
                'proposal_id': proposal.id,
                'method': 'internal',
                'acceptance_date': fields.Date.today(),
                'accepted_by': 'Mr Contact',
                'confirm_sale_order': True,
                'create_work_order': True,
            })
        action = wizard.action_confirm()
        work_order = self.env['gc.erm.work.order'].browse(action['res_id'])
        # SRS 29 -- the implementation team is assigned right after creation.
        # It is also what makes the work order visible to the implementation
        # user through the record rules of SRS 68.
        work_order.write({
            'team_id': self.team_impl.id,
            'engineer_id': self.user_impl.id,
            'manager_id': self.user_impl.id,
        })
        return work_order

    def _validate_picking(self, picking):
        picking = picking.with_context(skip_sms=True, skip_backorder=True)
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        result = picking.button_validate()
        if isinstance(result, dict) and result.get('res_model'):
            model = self.env[result['res_model']].with_context(
                **(result.get('context') or {}))
            wizard = model.browse(result['res_id']) if result.get('res_id') \
                else model.create({})
            if hasattr(wizard, 'process'):
                wizard.process()
        return picking.state
