# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install')
class TestRealEstateConstruction(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env['real.estate.project'].create({'project_name': 'Construction Test Project'})
        self.budget = self.env['real.estate.project.budget'].create({'project_id': self.project.id})
        self.allocation = self.env['real.estate.budget.allocation'].create({
            'budget_id': self.budget.id,
            'budget_head': 'materials',
            'allocated_amount': 100000.0,
        })

    def test_budget_totals_computed(self):
        self.env['real.estate.budget.allocation'].create({
            'budget_id': self.budget.id,
            'budget_head': 'civil',
            'allocated_amount': 50000.0,
            'committed_amount': 10000.0,
        })
        self.assertEqual(self.budget.total_budget, 150000.0)
        self.assertEqual(self.budget.total_committed, 10000.0)

    def test_budget_availability_blocks_overspend(self):
        with self.assertRaises(UserError):
            self.allocation.check_budget_availability(150000.0)

    def test_budget_availability_allows_within_limit(self):
        remaining = self.allocation.check_budget_availability(40000.0)
        self.assertEqual(remaining, 60000.0)

    def test_budget_allow_overspend_flag(self):
        self.allocation.allow_overspend = True
        # should not raise even though it exceeds remaining
        remaining = self.allocation.check_budget_availability(150000.0)
        self.assertEqual(remaining, -50000.0)

    def test_budget_transfer_moves_amounts(self):
        dest = self.env['real.estate.budget.allocation'].create({
            'budget_id': self.budget.id,
            'budget_head': 'interior',
            'allocated_amount': 20000.0,
        })
        transfer = self.env['real.estate.budget.transfer'].create({
            'source_allocation_id': self.allocation.id,
            'destination_allocation_id': dest.id,
            'amount': 15000.0,
            'reason': 'Reallocate for interior finishing priority.',
        })
        transfer.action_submit()
        transfer.action_approve()
        self.assertEqual(self.allocation.allocated_amount, 85000.0)
        self.assertEqual(dest.allocated_amount, 35000.0)
        self.assertEqual(transfer.state, 'approved')

    def test_budget_transfer_exceeding_source_blocked(self):
        dest = self.env['real.estate.budget.allocation'].create({
            'budget_id': self.budget.id,
            'budget_head': 'interior',
            'allocated_amount': 20000.0,
        })
        transfer = self.env['real.estate.budget.transfer'].create({
            'source_allocation_id': self.allocation.id,
            'destination_allocation_id': dest.id,
            'amount': 999999.0,
            'reason': 'Too much.',
        })
        transfer.action_submit()
        with self.assertRaises(UserError):
            transfer.action_approve()

    def test_work_package_hierarchy_and_progress(self):
        parent = self.env['real.estate.work.package'].create({
            'work_name': 'Construction', 'project_id': self.project.id,
        })
        child = self.env['real.estate.work.package'].create({
            'work_name': 'Foundation', 'project_id': self.project.id,
            'parent_id': parent.id, 'planned_quantity': 100, 'completed_quantity': 60,
        })
        self.assertEqual(child.progress, 60.0)
        self.assertIn(child, parent.child_ids)

    def test_work_package_self_loop_blocked(self):
        wp = self.env['real.estate.work.package'].create({
            'work_name': 'Loop Test', 'project_id': self.project.id,
        })
        with self.assertRaises(ValidationError):
            wp.write({'parent_id': wp.id})

    def test_requisition_estimated_cost_and_budget_approval(self):
        req = self.env['real.estate.requisition'].create({
            'project_id': self.project.id,
            'budget_allocation_id': self.allocation.id,
        })
        product = self.env['product.product'].create({'name': 'Test Bricks', 'type': 'consu'})
        self.env['real.estate.requisition.line'].create({
            'requisition_id': req.id,
            'product_id': product.id,
            'quantity': 1000,
            'estimated_rate': 12.0,
        })
        self.assertEqual(req.estimated_cost, 12000.0)

        req.action_submit()
        req.action_pm_approve()
        req.action_budget_approve()
        self.assertEqual(req.state, 'budget_approval')
        self.assertEqual(self.allocation.committed_amount, 12000.0)

    def test_requisition_budget_approval_blocked_when_over_budget(self):
        req = self.env['real.estate.requisition'].create({
            'project_id': self.project.id,
            'budget_allocation_id': self.allocation.id,
        })
        product = self.env['product.product'].create({'name': 'Expensive Item', 'type': 'consu'})
        self.env['real.estate.requisition.line'].create({
            'requisition_id': req.id,
            'product_id': product.id,
            'quantity': 1,
            'estimated_rate': 500000.0,
        })
        req.action_submit()
        req.action_pm_approve()
        with self.assertRaises(UserError):
            req.action_budget_approve()

    def test_contractor_bill_net_amount(self):
        partner = self.env['res.partner'].create({'name': 'Test Contractor Co.'})
        contractor = self.env['real.estate.contractor'].create({
            'partner_id': partner.id,
            'trade': 'civil',
            'retention_percentage': 10.0,
        })
        bill = self.env['real.estate.contractor.bill'].create({
            'contractor_id': contractor.id,
            'approved_quantity': 100,
            'rate': 1000.0,
            'advance_adjustment': 2000.0,
            'deduction': 500.0,
        })
        # gross = 100,000 ; retention = 10,000 ; net = 100,000 - 10,000 - 2,000 - 500
        self.assertEqual(bill.gross_amount, 100000.0)
        self.assertEqual(bill.retention_amount, 10000.0)
        self.assertEqual(bill.net_amount, 87500.0)
