# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestRealEstateQc(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env['real.estate.project'].create({'project_name': 'QC Test Project'})
        self.building = self.env['real.estate.building'].create({
            'building_name': 'QC Tower', 'project_id': self.project.id})
        self.floor = self.env['real.estate.floor'].create({
            'floor_name': 'Floor 1', 'floor_number': 1, 'building_id': self.building.id})
        self.unit = self.env['real.estate.unit'].create({
            'name': 'Q-101', 'floor_id': self.floor.id,
            'pricing_method': 'fixed', 'fixed_base_price': 1000000,
        })

    def test_inspection_sequence_generated(self):
        inspection = self.env['real.estate.qc.inspection'].create({'project_id': self.project.id})
        self.assertTrue(inspection.name.startswith('QC-'))

    def test_recommend_result_all_pass(self):
        inspection = self.env['real.estate.qc.inspection'].create({'project_id': self.project.id})
        self.env['real.estate.qc.inspection.line'].create({
            'inspection_id': inspection.id, 'item_name': 'Foundation', 'result': 'pass'})
        self.env['real.estate.qc.inspection.line'].create({
            'inspection_id': inspection.id, 'item_name': 'Column', 'result': 'pass'})
        inspection.action_recommend_result()
        self.assertEqual(inspection.result, 'passed')

    def test_recommend_result_any_fail(self):
        inspection = self.env['real.estate.qc.inspection'].create({'project_id': self.project.id})
        self.env['real.estate.qc.inspection.line'].create({
            'inspection_id': inspection.id, 'item_name': 'Foundation', 'result': 'pass'})
        self.env['real.estate.qc.inspection.line'].create({
            'inspection_id': inspection.id, 'item_name': 'Column', 'result': 'fail'})
        inspection.action_recommend_result()
        self.assertEqual(inspection.result, 'failed')

    def test_defect_sequence_and_workflow(self):
        defect = self.env['real.estate.defect'].create({
            'project_id': self.project.id,
            'unit_id': self.unit.id,
            'description': 'Test crack',
            'severity': 'high',
        })
        self.assertTrue(defect.name.startswith('DEF-'))
        self.assertEqual(defect.status, 'open')

        with self.assertRaises(UserError):
            defect.action_assign()  # no assignee set yet

        defect.assigned_user_id = self.env.user
        defect.action_assign()
        self.assertEqual(defect.status, 'assigned')
        defect.action_start_progress()
        defect.action_mark_fixed()
        defect.action_send_reinspection()
        defect.action_close()
        self.assertEqual(defect.status, 'closed')

    def test_unit_cannot_be_ready_with_open_critical_defect(self):
        self.env['real.estate.defect'].create({
            'project_id': self.project.id,
            'unit_id': self.unit.id,
            'description': 'Structural crack',
            'severity': 'critical',
        })
        with self.assertRaises(UserError):
            self.unit.action_set_ready()

    def test_unit_can_be_ready_once_defect_closed(self):
        defect = self.env['real.estate.defect'].create({
            'project_id': self.project.id,
            'unit_id': self.unit.id,
            'description': 'Structural crack',
            'severity': 'critical',
        })
        defect.status = 'closed'
        self.unit.action_set_ready()
        self.assertEqual(self.unit.status, 'ready')

    def test_project_readiness_gate_blocks_without_checklist(self):
        self.project.write({'state': 'draft'})
        self.project.action_start_planning()
        self.project.action_approve()
        self.project.action_start_construction()
        self.project.action_move_to_qc()
        # no readiness checkboxes ticked, no defects/inspections -> should block
        with self.assertRaises(UserError):
            self.project.action_mark_ready()

    def test_project_readiness_gate_blocks_on_failed_inspection(self):
        self.project.write({
            'state': 'qc',
            'readiness_utilities_completed': True,
            'readiness_documentation_completed': True,
            'readiness_safety_completed': True,
        })
        self.env['real.estate.qc.inspection'].create({
            'project_id': self.project.id, 'result': 'failed',
        })
        with self.assertRaises(UserError):
            self.project.action_mark_ready()

    def test_project_readiness_gate_passes_when_clear(self):
        self.project.write({
            'state': 'qc',
            'readiness_utilities_completed': True,
            'readiness_documentation_completed': True,
            'readiness_safety_completed': True,
        })
        self.project.action_mark_ready()
        self.assertEqual(self.project.state, 'ready')
