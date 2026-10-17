# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

APPLY = {'bond_classification_apply': True}


@tagged('post_install', '-at_install')
class TestBondInventory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        parent = cls.warehouse.view_location_id
        Location = cls.env['stock.location']
        cls.bond_loc = Location.with_context(**APPLY).create({
            'name': 'BOND-A', 'usage': 'internal', 'location_id': parent.id,
            'bond_status': 'bonded', 'bond_license_ref': 'TEST-LICENSE-1'})
        cls.free_loc = Location.create({'name': 'FREE-A', 'usage': 'internal', 'location_id': parent.id})
        cls.free_loc2 = Location.create({'name': 'FREE-B', 'usage': 'internal', 'location_id': parent.id})
        cls.partner = cls.env['res.partner'].create({'name': 'Test Supplier'})
        Product = cls.env['product.product'].with_context(**APPLY)
        vals = {'detailed_type': 'product', 'tracking': 'lot'}
        cls.leather = Product.create(dict(vals, name='Test Leather', bond_eligible=True, bond_hs_code='HS-TEST'))
        cls.chemical = Product.create(dict(vals, name='Test Chemical', bond_eligible=True,
                                           bond_hs_code='HS-TEST-2', bond_requires_expiry=True))
        cls.plain = Product.create(dict(vals, name='Test Plain'))

    # -- helpers --------------------------------------------------------------
    def _consignment(self, product, qty, boe='BOE-T-1'):
        cons = self.env['bond.inventory.consignment'].create({
            'partner_id': self.partner.id, 'lc_number': 'LC-T-1', 'boe_number': boe,
            'line_ids': [(0, 0, {'product_id': product.id, 'declared_qty': qty, 'hs_code': 'HS-TEST'})]})
        cons.action_open()
        return cons

    def _receipt(self, product, declared, bond_status='bonded', location=None, consignment=None, boe='BOE-T-1'):
        vals = {
            'partner_id': self.partner.id, 'bond_status': bond_status,
            'location_dest_id': (location or (self.bond_loc if bond_status == 'bonded' else self.free_loc)).id,
            'lc_number': 'LC-T-1', 'boe_number': boe,
            'line_ids': [(0, 0, {'product_id': product.id, 'declared_qty': declared, 'hs_code': 'HS-TEST'})],
        }
        if consignment:
            vals['consignment_id'] = consignment.id
            vals['line_ids'][0][2]['consignment_line_id'] = consignment.line_ids[0].id
        return self.env['bond.inventory.receipt'].create(vals)

    def _verify_docs(self, receipt):
        attachment = self.env['ir.attachment'].create({'name': 'boe.pdf', 'raw': b'boe'})
        doc = self.env['bond.inventory.receipt.document'].create({
            'receipt_id': receipt.id, 'type_id': self.env.ref('nelsis_bond_inventory.doc_type_bill_of_entry').id,
            'reference': 'BOE-T', 'attachment_ids': [(6, 0, attachment.ids)]})
        doc.action_verify()

    def _to_inspection(self, receipt):
        receipt.action_submit_verification()
        if receipt.bond_status == 'bonded':
            self._verify_docs(receipt)
        receipt.action_verify_documents()

    def _inspect(self, receipt, received, damaged=0.0, rejected=0.0, lot='LOT-1', expiry=False):
        receipt.line_ids.write({'received_qty': received, 'damaged_qty': damaged, 'rejected_qty': rejected,
                                'lot_name': lot, 'expiry_date': expiry, 'inspected': True})
        receipt.action_complete_inspection()
        if receipt.state == 'approval':
            receipt.action_approve()

    def _run(self, receipt, received, **kw):
        self._to_inspection(receipt)
        self._inspect(receipt, received, **kw)
        return receipt

    def _qty(self, product, location, lot=None):
        domain = [('product_id', '=', product.id), ('location_id', '=', location.id)]
        if lot:
            domain.append(('lot_id', '=', lot.id))
        return sum(self.env['stock.quant'].search(domain).mapped('quantity'))

    # -- tests ----------------------------------------------------------------
    def test_01_full_bonded_receipt_posts_stock_and_traceability(self):
        receipt = self._run(self._receipt(self.leather, 100.0), 100.0)
        self.assertEqual(receipt.state, 'ready')
        self.assertFalse(receipt.picking_id)
        self.assertEqual(self._qty(self.leather, self.bond_loc), 0.0)
        receipt.action_validate()
        self.assertEqual(receipt.state, 'done')
        self.assertEqual(receipt.picking_id.state, 'done')
        self.assertEqual(receipt.picking_id.bond_receipt_id, receipt)
        lot = receipt.line_ids.lot_id
        self.assertEqual(lot.bond_status, 'bonded')
        self.assertEqual(lot.bond_boe_number, 'BOE-T-1')
        self.assertEqual(lot.bond_lc_label, 'LC-T-1')
        self.assertEqual(lot.bond_receipt_id, receipt)
        self.assertEqual(self._qty(self.leather, self.bond_loc, lot), 100.0)
        report = self.env['bond.inventory.stock.report'].search([('lot_id', '=', lot.id)])
        self.assertEqual(sum(report.mapped('quantity')), 100.0)
        self.assertEqual(report.boe_number, 'BOE-T-1')

    def test_02_partial_receipts_against_consignment(self):
        cons = self._consignment(self.leather, 100.0)
        first = self._run(self._receipt(self.leather, 60.0, consignment=cons), 60.0, lot='P-1')
        first.action_validate()
        self.assertEqual(cons.line_ids.received_qty, 60.0)
        self.assertEqual(cons.line_ids.remaining_qty, 40.0)
        second = self._receipt(self.leather, 40.0, consignment=cons)
        self._run(second, 40.0, lot='P-2')
        second.action_validate()
        self.assertEqual(cons.line_ids.remaining_qty, 0.0)
        self.assertEqual(self._qty(self.leather, self.bond_loc), 100.0)
        self.assertEqual(cons.receipt_count, 2)

    def test_03_duplicate_validation_is_blocked(self):
        receipt = self._run(self._receipt(self.leather, 10.0), 10.0)
        receipt.action_validate()
        with self.assertRaises(UserError):
            receipt.action_validate()
        with self.assertRaises(UserError):
            receipt.picking_id.button_validate()
        self.assertEqual(self._qty(self.leather, self.bond_loc), 10.0)

    def test_04_shortage_damaged_rejected_need_approval(self):
        receipt = self._receipt(self.leather, 100.0)
        self._to_inspection(receipt)
        receipt.line_ids.write({'received_qty': 90.0, 'damaged_qty': 5.0, 'rejected_qty': 5.0,
                                'lot_name': 'SH-1', 'inspected': True})
        line = receipt.line_ids
        self.assertEqual((line.accepted_qty, line.shortage_qty, line.excess_qty), (80.0, 10.0, 0.0))
        receipt.action_complete_inspection()
        self.assertEqual(receipt.state, 'approval')
        receipt.action_approve()
        receipt.action_validate()
        self.assertEqual(self._qty(self.leather, self.bond_loc), 80.0)

    def test_05_excess_is_tracked(self):
        receipt = self._receipt(self.leather, 10.0)
        self._to_inspection(receipt)
        receipt.line_ids.write({'received_qty': 12.0, 'lot_name': 'EX-1', 'inspected': True})
        self.assertEqual(receipt.line_ids.excess_qty, 2.0)
        receipt.action_complete_inspection()
        self.assertEqual(receipt.state, 'approval')

    def test_06_rejected_receipt_creates_no_stock(self):
        receipt = self._receipt(self.leather, 10.0)
        self._to_inspection(receipt)
        with self.assertRaises(UserError):
            receipt.action_reject()
        receipt.reject_reason = 'Goods do not match the Bill of Entry'
        receipt.action_reject()
        self.assertEqual(receipt.state, 'rejected')
        self.assertFalse(receipt.picking_id)
        self.assertEqual(self._qty(self.leather, self.bond_loc), 0.0)

    def test_07_all_goods_rejected_cannot_complete(self):
        receipt = self._receipt(self.leather, 10.0)
        self._to_inspection(receipt)
        receipt.line_ids.write({'received_qty': 10.0, 'rejected_qty': 10.0, 'lot_name': 'RJ-1', 'inspected': True})
        with self.assertRaises(UserError):
            receipt.action_complete_inspection()

    def test_08_unauthorized_location(self):
        with self.assertRaises(ValidationError):
            self._receipt(self.leather, 5.0, bond_status='bonded', location=self.free_loc)
        with self.assertRaises(ValidationError):
            self._receipt(self.leather, 5.0, bond_status='non_bonded', location=self.bond_loc)
        self.bond_loc.with_context(**APPLY).write({'bond_authorized_to': '2000-01-01'})
        receipt = self._receipt(self.leather, 5.0)
        with self.assertRaises(UserError):
            receipt.action_submit_verification()

    def test_09_bonded_non_bonded_separation(self):
        bonded = self._run(self._receipt(self.leather, 50.0), 50.0, lot='B-1')
        bonded.action_validate()
        plain = self._run(self._receipt(self.leather, 30.0, bond_status='non_bonded'), 30.0, lot='N-1')
        plain.action_validate()
        blot, nlot = bonded.line_ids.lot_id, plain.line_ids.lot_id
        self.assertEqual((blot.bond_status, nlot.bond_status), ('bonded', 'non_bonded'))
        self.assertEqual(self._qty(self.leather, self.bond_loc), 50.0)
        self.assertEqual(self._qty(self.leather, self.free_loc), 30.0)
        # bonded lot cannot move to a non-bonded location, non-bonded lot cannot enter bond
        for lot, src, dst in ((blot, self.bond_loc, self.free_loc2), (nlot, self.free_loc, self.bond_loc)):
            move = self.env['stock.move'].create({
                'name': 'illegal', 'product_id': self.leather.id, 'product_uom_qty': 5.0,
                'product_uom': self.leather.uom_id.id, 'location_id': src.id, 'location_dest_id': dst.id,
                'move_line_ids': [(0, 0, {
                    'product_id': self.leather.id, 'product_uom_id': self.leather.uom_id.id, 'quantity': 5.0,
                    'lot_id': lot.id, 'location_id': src.id, 'location_dest_id': dst.id, 'picked': True})]})
            move.picked = True
            with self.assertRaises(UserError):
                move._action_done()
        self.assertEqual(self._qty(self.leather, self.bond_loc), 50.0)

    def test_10_non_eligible_product_cannot_be_received_as_bonded(self):
        receipt = self._receipt(self.plain, 5.0)
        with self.assertRaises(UserError):
            receipt.action_submit_verification()

    def test_11_lot_and_expiry_are_mandatory(self):
        receipt = self._receipt(self.leather, 5.0)
        self._to_inspection(receipt)
        receipt.line_ids.write({'received_qty': 5.0, 'inspected': True})
        with self.assertRaises(UserError):
            receipt.action_complete_inspection()
        chem = self._receipt(self.chemical, 5.0, boe='BOE-T-2')
        self._to_inspection(chem)
        chem.line_ids.write({'received_qty': 5.0, 'lot_name': 'CH-1', 'inspected': True})
        with self.assertRaises(UserError):
            chem.action_complete_inspection()
        chem.line_ids.write({'expiry_date': '2030-01-01'})
        chem.action_complete_inspection()
        chem.action_validate()
        self.assertEqual(str(chem.line_ids.lot_id.bond_expiry_date), '2030-01-01')

    def test_12_classification_changes_need_workflow_and_evidence(self):
        with self.assertRaises(UserError):
            self.leather.product_tmpl_id.with_context(bond_classification_apply=False).write(
                {'bond_eligible': False})
        with self.assertRaises(UserError):
            self.free_loc.write({'bond_status': 'bonded'})
        request = self.env['bond.inventory.classification.request'].create({
            'target_type': 'location', 'location_id': self.free_loc2.id, 'new_status': 'bonded',
            'license_ref': 'TEST-LICENSE-2', 'reason': 'New bonded area approved'})
        with self.assertRaises(UserError):
            request.action_submit()
        attachment = self.env['ir.attachment'].create({'name': 'evidence.pdf', 'raw': b'x'})
        request.attachment_ids = [(6, 0, attachment.ids)]
        request.action_submit()
        request.action_approve()
        self.assertEqual(request.state, 'applied')
        self.assertEqual(self.free_loc2.bond_status, 'bonded')
        self.assertEqual(self.free_loc2.bond_license_ref, 'TEST-LICENSE-2')

    def test_13_cannot_reclassify_location_holding_stock(self):
        self._run(self._receipt(self.leather, 5.0), 5.0).action_validate()
        request = self.env['bond.inventory.classification.request'].create({
            'target_type': 'location', 'location_id': self.bond_loc.id, 'new_status': 'non_bonded',
            'reason': 'test'})
        attachment = self.env['ir.attachment'].create({'name': 'evidence.pdf', 'raw': b'x'})
        request.attachment_ids = [(6, 0, attachment.ids)]
        request.action_submit()
        with self.assertRaises(UserError):
            request.action_approve()

    def test_14_leather_uoms_are_not_implicitly_converted(self):
        sqft = self.env.ref('nelsis_bond_inventory.uom_sqft_leather')
        sqm = self.env.ref('nelsis_bond_inventory.uom_sqm_leather')
        self.assertEqual(sqm._compute_quantity(1.0, sqft), 10.764)
        with self.assertRaises(UserError):
            self.env.ref('uom.product_uom_unit')._compute_quantity(1.0, sqft)
        hides = self.leather
        with self.assertRaises(ValidationError):
            self.env['bond.inventory.receipt.line'].new({'product_id': hides.id, 'product_uom_id': sqft.id}) \
                ._check_uom()

    def test_15_direct_stock_receipt_into_bond_is_blocked(self):
        lot = self.env['stock.lot'].with_context(**APPLY).create({
            'name': 'DIRECT-1', 'product_id': self.leather.id, 'company_id': self.company.id,
            'bond_status': 'bonded'})
        supplier = self.env.ref('stock.stock_location_suppliers')
        move = self.env['stock.move'].create({
            'name': 'direct', 'product_id': self.leather.id, 'product_uom_qty': 3.0,
            'product_uom': self.leather.uom_id.id, 'location_id': supplier.id, 'location_dest_id': self.bond_loc.id,
            'move_line_ids': [(0, 0, {
                'product_id': self.leather.id, 'product_uom_id': self.leather.uom_id.id, 'quantity': 3.0,
                'lot_id': lot.id, 'location_id': supplier.id, 'location_dest_id': self.bond_loc.id,
                'picked': True})]})
        move.picked = True
        with self.assertRaises(UserError):
            move._action_done()
