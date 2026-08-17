# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestRealEstateHandover(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env['real.estate.project'].create({'project_name': 'Handover Test Project'})
        self.building = self.env['real.estate.building'].create({
            'building_name': 'Handover Tower', 'project_id': self.project.id})
        self.floor = self.env['real.estate.floor'].create({
            'floor_name': 'Floor 1', 'floor_number': 1, 'building_id': self.building.id})
        self.unit = self.env['real.estate.unit'].create({
            'name': 'H-101', 'floor_id': self.floor.id,
            'pricing_method': 'fixed', 'fixed_base_price': 5000000,
        })
        self.customer = self.env['res.partner'].create({'name': 'Handover Buyer'})
        self.agreement = self.env['real.estate.sale.agreement'].create({
            'customer_id': self.customer.id,
            'unit_id': self.unit.id,
            'total_price': 5000000,
        })
        self.agreement.action_activate()

    def _new_handover(self, **overrides):
        vals = {
            'unit_id': self.unit.id,
            'sale_agreement_id': self.agreement.id,
        }
        vals.update(overrides)
        return self.env['real.estate.handover'].create(vals)

    def test_sequence_and_default_checklist(self):
        handover = self._new_handover()
        self.assertTrue(handover.name.startswith('HAND-'))
        self.assertEqual(len(handover.checklist_line_ids), 12)

    def test_financial_clearance_blocked_with_outstanding_balance(self):
        handover = self._new_handover()
        handover.action_request()
        with self.assertRaises(UserError):
            handover.action_financial_clearance()

    def test_financial_clearance_passes_with_override(self):
        handover = self._new_handover(financial_override=True,
                                        financial_override_reason='Management approved partial waiver.')
        handover.action_request()
        handover.action_financial_clearance()
        self.assertEqual(handover.state, 'financial_clearance')

    def test_financial_clearance_passes_when_fully_paid(self):
        collection = self.env['real.estate.collection'].create({
            'customer_id': self.customer.id,
            'sale_agreement_id': self.agreement.id,
            'amount': 5000000,
        })
        collection.action_confirm()
        handover = self._new_handover()
        handover.action_request()
        handover.action_financial_clearance()
        self.assertEqual(handover.state, 'financial_clearance')

    def test_qc_clearance_blocked_without_passed_final_inspection(self):
        collection = self.env['real.estate.collection'].create({
            'customer_id': self.customer.id, 'sale_agreement_id': self.agreement.id, 'amount': 5000000,
        })
        collection.action_confirm()
        handover = self._new_handover()
        handover.action_request()
        handover.action_financial_clearance()
        with self.assertRaises(UserError):
            handover.action_qc_clearance()

    def test_qc_clearance_blocked_by_open_critical_defect(self):
        self.env['real.estate.qc.inspection'].create({
            'project_id': self.project.id, 'unit_id': self.unit.id,
            'inspection_type': 'final', 'result': 'passed',
        })
        self.env['real.estate.defect'].create({
            'project_id': self.project.id, 'unit_id': self.unit.id,
            'description': 'Cracked tile', 'severity': 'critical',
        })
        collection = self.env['real.estate.collection'].create({
            'customer_id': self.customer.id, 'sale_agreement_id': self.agreement.id, 'amount': 5000000,
        })
        collection.action_confirm()
        handover = self._new_handover()
        handover.action_request()
        handover.action_financial_clearance()
        with self.assertRaises(UserError):
            handover.action_qc_clearance()

    def test_full_happy_path_to_handed_over(self):
        # Financial: fully paid
        collection = self.env['real.estate.collection'].create({
            'customer_id': self.customer.id, 'sale_agreement_id': self.agreement.id, 'amount': 5000000,
        })
        collection.action_confirm()
        # QC: passed final inspection, no critical defects
        self.env['real.estate.qc.inspection'].create({
            'project_id': self.project.id, 'unit_id': self.unit.id,
            'inspection_type': 'final', 'result': 'passed',
        })

        handover = self._new_handover()
        handover.action_request()
        self.assertEqual(self.unit.status, 'handover_pending')

        handover.action_financial_clearance()
        handover.action_qc_clearance()

        # Documentation: not yet ticked -> blocked
        with self.assertRaises(UserError):
            handover.action_documentation_clearance()

        handover.write({
            'doc_agreement_signed': True,
            'doc_customer_documents': True,
            'doc_payment_records': True,
            'doc_legal_documents': True,
        })
        handover.action_documentation_clearance()
        handover.action_final_inspection()
        handover.action_approve()

        # Missing signatures -> blocked
        with self.assertRaises(UserError):
            handover.action_handover()

        handover.write({'customer_signed': True, 'company_signed': True})
        handover.action_handover()
        self.assertEqual(handover.state, 'handed_over')
        self.assertEqual(self.unit.status, 'handed_over')

        handover.action_complete()
        self.assertEqual(handover.state, 'completed')

    def test_print_certificate_action_resolves(self):
        handover = self._new_handover()
        report_action = self.env.ref(
            'real_estate_project_management.action_report_real_estate_handover')
        self.assertEqual(report_action.model, 'real.estate.handover')
        self.assertEqual(report_action.report_type, 'qweb-pdf')
