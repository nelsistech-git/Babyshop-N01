# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

APPLY = {'bond_classification_apply': True}


@tagged('post_install', '-at_install')
class TestBondPurchase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.bond_po_entitlement_policy = 'off'
        today = fields.Date.today()
        cls.today = today
        wh = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        parent = wh.view_location_id
        cls.bond_loc = cls.env['stock.location'].with_context(**APPLY).create({
            'name': 'BOND-PO', 'usage': 'internal', 'location_id': parent.id,
            'bond_status': 'bonded', 'bond_license_ref': 'TEST-LICENSE-PO'})
        cls.supplier = cls.env['res.partner'].create({'name': 'PO Test Supplier'})
        cls.other_supplier = cls.env['res.partner'].create({'name': 'PO Other Supplier'})
        cls.bank = cls.env['res.bank'].create({'name': 'PO Test Bank'})
        Product = cls.env['product.product'].with_context(**APPLY)
        vals = {'detailed_type': 'product', 'tracking': 'lot'}
        cls.leather = Product.create(dict(vals, name='PO Leather', bond_eligible=True, bond_hs_code='HS-PO-1',
                                          standard_price=1.0))
        cls.plain = Product.create(dict(vals, name='PO Plain'))
        cls.local_product = cls.env['product.product'].create({'name': 'PO Carton', 'detailed_type': 'product'})

    # ------------------------------------------------------------------ helpers
    def _lc(self, amount=10000.0, supplier=None, state='opened', number=None, tolerance=5.0):
        lc = self.env['nelsis.lc'].create({
            'partner_id': (supplier or self.supplier).id, 'bank_id': self.bank.id, 'original_amount': amount,
            'lc_number': number or 'PO-LC-%s' % self.env['nelsis.lc'].search_count([]),
            'opening_date': self.today, 'expiry_date': self.today + timedelta(days=90),
            'shipment_deadline': self.today + timedelta(days=60), 'tolerance_percent': tolerance})
        if state != 'draft':
            lc.action_submit()
            lc.action_approve()
            if state in ('opened',):
                lc.action_open()
        return lc

    def _po(self, lines=None, kind='import_bonded', lc=None, supplier=None, **kw):
        lines = lines or [(self.leather, 100.0, 5.0)]
        vals = {'partner_id': (supplier or self.supplier).id, 'bond_purchase_type': kind,
                'order_line': [(0, 0, {'product_id': p.id, 'name': p.name, 'product_qty': q, 'price_unit': pr,
                                       'date_planned': fields.Datetime.now(), 'taxes_id': [(5, 0, 0)]})
                               for p, q, pr in lines]}
        if lc:
            vals['lc_id'] = lc.id
        vals.update(kw)
        return self.env['purchase.order'].create(vals)

    def _verify_docs(self, receipt):
        att = self.env['ir.attachment'].create({'name': 'boe.pdf', 'raw': b'boe'})
        doc = self.env['bond.inventory.receipt.document'].create({
            'receipt_id': receipt.id, 'type_id': self.env.ref('nelsis_bond_inventory.doc_type_bill_of_entry').id,
            'reference': 'BOE-T', 'attachment_ids': [(6, 0, att.ids)]})
        doc.action_verify()

    def _receive(self, cons, qty, lot):
        receipt = self.env['bond.inventory.receipt'].create({
            'partner_id': cons.partner_id.id, 'bond_status': 'bonded', 'location_dest_id': self.bond_loc.id,
            'consignment_id': cons.id, 'lc_number': cons.lc_number, 'boe_number': cons.boe_number,
            'line_ids': [(0, 0, {'consignment_line_id': cons.line_ids[0].id, 'product_id': cons.line_ids[0].product_id.id,
                                 'declared_qty': qty, 'hs_code': 'HS-PO-1'})]})
        receipt.action_submit_verification()
        self._verify_docs(receipt)
        receipt.action_verify_documents()
        receipt.line_ids.write({'received_qty': qty, 'lot_name': lot, 'inspected': True})
        receipt.action_complete_inspection()
        if receipt.state == 'approval':
            receipt.action_approve()
        receipt.action_validate()
        return receipt

    def _consignment(self, po, boe='BOE-PO-1'):
        action = po.action_bond_create_consignment()
        cons = self.env['bond.inventory.consignment'].browse(action['res_id'])
        cons.write({'boe_number': boe})
        cons.action_open()
        return cons

    # -------------------------------------------------------------------- tests
    def test_01_bonded_confirm_needs_lc(self):
        po = self._po()
        with self.assertRaises(UserError):
            po.button_confirm()
        self.company.bond_po_require_lc = False
        po.button_confirm()
        self.assertEqual(po.state, 'purchase')
        self.company.bond_po_require_lc = True

    def test_02_bonded_order_creates_no_standard_receipt(self):
        po = self._po(lc=self._lc())
        po.button_confirm()
        self.assertEqual(po.state, 'purchase')
        self.assertFalse(po.picking_ids)
        self.assertEqual(po.receipt_status, 'pending')

    def test_03_local_order_keeps_standard_receipt(self):
        po = self._po(lines=[(self.local_product, 10.0, 2.0)], kind='local')
        po.button_confirm()
        self.assertEqual(len(po.picking_ids), 1)

    def test_04_product_checks_block_confirmation(self):
        po = self._po(lines=[(self.plain, 10.0, 2.0)], lc=self._lc())
        with self.assertRaises(UserError):
            po.button_confirm()
        dup = self._po(lines=[(self.leather, 10.0, 2.0), (self.leather, 5.0, 2.0)], lc=self._lc())
        with self.assertRaises(UserError):
            dup.button_confirm()

    def test_05_lc_must_match_supplier_and_currency(self):
        lc = self._lc()
        with self.assertRaises(ValidationError):
            self._po(lc=lc, supplier=self.other_supplier)
        other = self.env['res.currency'].with_context(active_test=False).search(
            [('id', '!=', self.company.currency_id.id)], limit=1)
        other.active = True
        with self.assertRaises(ValidationError):
            self._po(lc=lc, currency_id=other.id)

    def test_06_lc_limit_blocks_and_tracks_commitment(self):
        lc = self._lc(amount=1000.0)
        first = self._po(lines=[(self.leather, 100.0, 9.0)], lc=lc)   # 900
        first.button_confirm()
        self.assertEqual(lc.po_committed_amount, 900.0)
        self.assertEqual(lc.purchase_count, 1)
        second = self._po(lines=[(self.leather, 100.0, 2.0)], lc=lc)  # 900 + 200 > 1000 + 5%
        with self.assertRaises(UserError):
            second.button_confirm()
        self.company.bond_po_lc_limit_policy = 'warn'
        second.button_confirm()
        self.assertEqual(second.state, 'purchase')
        self.company.bond_po_lc_limit_policy = 'block'

    def test_07_lc_on_hold_blocks_confirmation(self):
        lc = self._lc()
        po = self._po(lc=lc)
        lc.sudo().write({'state': 'hold'})
        with self.assertRaises(UserError):
            po.button_confirm()

    def test_08_consignment_from_order_and_over_declaration(self):
        lc = self._lc()
        po = self._po(lines=[(self.leather, 100.0, 5.0)], lc=lc)
        po.button_confirm()
        self.assertTrue(po.bond_has_uncovered_qty)
        cons = self._consignment(po)
        self.assertEqual(cons.purchase_order_id, po)
        self.assertEqual(cons.lc_number, lc.lc_number)
        self.assertEqual(cons.line_ids.declared_qty, 100.0)
        self.assertEqual(po.order_line.bond_uncovered_qty, 0.0)
        self.assertFalse(po.bond_has_uncovered_qty)
        with self.assertRaises(UserError):
            po.action_bond_create_consignment()
        with self.assertRaises(ValidationError):
            cons.line_ids.declared_qty = 120.0   # above 100 + 5% tolerance

    def test_09_receipt_updates_purchase_line_price_and_references(self):
        lc = self._lc()
        po = self._po(lines=[(self.leather, 100.0, 5.0)], lc=lc)
        po.button_confirm()
        file = self.env['nelsis.commercial.file'].browse(po.action_bond_create_commercial_file()['res_id'])
        self.assertEqual(po.commercial_file_id, file)
        cons = self._consignment(po)
        first = self._receive(cons, 60.0, 'PO-LOT-1')
        line = po.order_line
        self.assertEqual(line.qty_received, 60.0)
        self.assertEqual(po.receipt_status, 'partial')
        self.assertEqual(po.bond_received_percent, 60.0)
        move = first.picking_id.move_ids
        self.assertEqual(move.purchase_line_id, line)
        self.assertEqual(move.price_unit, 5.0)
        picking = first.picking_id
        self.assertEqual(picking.lc_id, lc)
        self.assertEqual(picking.bond_lc_ref, lc.lc_number)
        self.assertEqual(picking.bond_boe_ref, 'BOE-PO-1')
        self.assertIn(picking, file.picking_ids)
        self.assertEqual(first.purchase_order_id, po)
        second = self._receive(cons, 40.0, 'PO-LOT-2')
        self.assertEqual(line.qty_received, 100.0)
        self.assertEqual(po.receipt_status, 'full')
        self.assertEqual(po.bond_receipt_count, 2)
        with self.assertRaises(UserError):
            line.product_qty = 50.0   # below the received quantity

    def test_10_sync_links_receipt_validated_before_the_order(self):
        # a consignment received before it was linked to an order
        lc = self._lc()
        cons = self.env['bond.inventory.consignment'].create({
            'partner_id': self.supplier.id, 'lc_number': lc.lc_number, 'boe_number': 'BOE-PO-9',
            'lc_ref': 'nelsis.lc,%d' % lc.id,
            'line_ids': [(0, 0, {'product_id': self.leather.id, 'declared_qty': 50.0, 'hs_code': 'HS-PO-1'})]})
        cons.action_open()
        receipt = self._receive(cons, 50.0, 'PO-LOT-9')
        po = self._po(lines=[(self.leather, 50.0, 4.0)], lc=lc)
        po.button_confirm()
        self.assertEqual(po.order_line.qty_received, 0.0)
        cons.purchase_order_id = po
        po.action_bond_sync()
        self.assertEqual(cons.line_ids.purchase_line_id, po.order_line)
        self.assertEqual(po.order_line.qty_received, 50.0)
        self.assertEqual(receipt.picking_id.move_ids.purchase_line_id, po.order_line)
        self.assertEqual(po.action_bond_sync()['params']['type'], 'success')

    def test_11_commercial_file_lc_must_match(self):
        lc1, lc2 = self._lc(), self._lc()
        po = self._po(lc=lc1)
        file = self.env['nelsis.commercial.file'].create({
            'partner_id': self.supplier.id, 'transaction_type': 'import_lc',
            'lc_ref': 'nelsis.lc,%d' % lc2.id})
        with self.assertRaises(ValidationError):
            po.commercial_file_id = file

    def test_12_type_cannot_change_after_confirmation(self):
        po = self._po(lc=self._lc())
        po.button_confirm()
        with self.assertRaises(UserError):
            po.bond_purchase_type = 'local'

    def test_13_cancel_cancels_open_consignment(self):
        po = self._po(lc=self._lc())
        po.button_confirm()
        cons = self._consignment(po)
        po.button_cancel()
        self.assertEqual(po.state, 'cancel')
        self.assertEqual(cons.state, 'cancelled')
