# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestRealEstateWarranty(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env['real.estate.project'].create({'project_name': 'Warranty Test Project'})
        self.building = self.env['real.estate.building'].create({
            'building_name': 'Warranty Tower', 'project_id': self.project.id})
        self.floor = self.env['real.estate.floor'].create({
            'floor_name': 'Floor 1', 'floor_number': 1, 'building_id': self.building.id})
        self.unit = self.env['real.estate.unit'].create({
            'name': 'W-101', 'floor_id': self.floor.id,
            'pricing_method': 'fixed', 'fixed_base_price': 5000000,
        })
        self.customer = self.env['res.partner'].create({'name': 'Warranty Customer'})

    def _new_claim(self, **overrides):
        vals = {
            'customer_id': self.customer.id,
            'unit_id': self.unit.id,
            'category': 'plumbing',
            'description': 'Leaking tap in kitchen.',
        }
        vals.update(overrides)
        return self.env['real.estate.warranty'].create(vals)

    def test_sequence_generated(self):
        claim = self._new_claim()
        self.assertTrue(claim.name.startswith('WAR-'))
        self.assertEqual(claim.status, 'reported')

    def test_assign_requires_assignee(self):
        claim = self._new_claim()
        claim.action_start_inspection()
        with self.assertRaises(UserError):
            claim.action_assign()
        claim.assigned_user_id = self.env.user
        claim.action_assign()
        self.assertEqual(claim.status, 'assigned')

    def test_full_workflow_to_closed(self):
        claim = self._new_claim()
        claim.action_start_inspection()
        claim.assigned_user_id = self.env.user
        claim.action_assign()
        claim.action_start_repair()
        claim.action_send_qc()
        claim.action_close()
        self.assertEqual(claim.status, 'closed')
        claim.action_reopen()
        self.assertEqual(claim.status, 'reported')

    def test_out_of_sequence_action_blocked(self):
        claim = self._new_claim()
        with self.assertRaises(UserError):
            claim.action_start_repair()  # cannot skip inspection/assign

    def test_warranty_expiry_computed_from_handover(self):
        agreement = self.env['real.estate.sale.agreement'].create({
            'customer_id': self.customer.id,
            'unit_id': self.unit.id,
            'total_price': 5000000,
        })
        agreement.action_activate()
        collection = self.env['real.estate.collection'].create({
            'customer_id': self.customer.id, 'sale_agreement_id': agreement.id, 'amount': 5000000,
        })
        collection.action_confirm()
        self.env['real.estate.qc.inspection'].create({
            'project_id': self.project.id, 'unit_id': self.unit.id,
            'inspection_type': 'final', 'result': 'passed',
        })
        handover = self.env['real.estate.handover'].create({
            'unit_id': self.unit.id, 'sale_agreement_id': agreement.id,
            'handover_date': '2025-01-01', 'warranty_period_months': 12,
        })
        handover.action_request()
        handover.action_financial_clearance()
        handover.action_qc_clearance()
        handover.write({
            'doc_agreement_signed': True, 'doc_customer_documents': True,
            'doc_payment_records': True, 'doc_legal_documents': True,
        })
        handover.action_documentation_clearance()
        handover.action_final_inspection()
        handover.action_approve()
        handover.write({'customer_signed': True, 'company_signed': True})
        handover.action_handover()

        self.assertEqual(handover.warranty_expiry_date.isoformat(), '2026-01-01')

        claim_in_warranty = self._new_claim(handover_id=handover.id, reported_date='2025-06-01')
        self.assertTrue(claim_in_warranty.is_under_warranty)

        claim_out_of_warranty = self._new_claim(handover_id=handover.id, reported_date='2026-06-01')
        self.assertFalse(claim_out_of_warranty.is_under_warranty)
