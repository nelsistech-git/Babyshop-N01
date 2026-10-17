# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
import base64

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCommercial(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Supplier'})
        cls.type_ci = cls.env.ref('nelsis_commercial.doc_type_ci')
        cls.rule = cls.env['nelsis.commercial.rule'].create({
            'name': 'Test: invoice required', 'document_type_id': cls.type_ci.id,
            'requirement': 'required', 'transaction_type': 'import_lc'})
        cls.file = cls.env['nelsis.commercial.file'].create({
            'transaction_type': 'import_lc', 'partner_id': cls.partner.id})
        manager_group = cls.env.ref('nelsis_commercial.group_commercial_manager')
        user_group = cls.env.ref('nelsis_commercial.group_commercial_user')
        cls.manager = cls.env['res.users'].create({
            'name': 'Mgr', 'login': 'nc_mgr', 'groups_id': [(6, 0, [manager_group.id, cls.env.ref('base.group_user').id])]})
        cls.basic = cls.env['res.users'].create({
            'name': 'Basic', 'login': 'nc_basic', 'groups_id': [(6, 0, [user_group.id, cls.env.ref('base.group_user').id])]})

    def _attachment(self, name='ci.pdf', content=b'invoice-1'):
        return self.env['ir.attachment'].create({'name': name, 'datas': base64.b64encode(content)})

    def _doc(self, number='CI-1', content=b'invoice-1'):
        return self.env['nelsis.commercial.document'].create({
            'file_id': self.file.id, 'document_type_id': self.type_ci.id, 'number': number,
            'attachment_ids': [(6, 0, self._attachment(content=content).ids)]})

    def test_sequence_and_missing(self):
        self.assertTrue(self.file.name.startswith('NCF/'))
        self.assertEqual(self.file.missing_count, 1)

    def test_basic_user_cannot_verify(self):
        doc = self._doc()
        doc.action_submit()
        with self.assertRaises(AccessError):
            doc.with_user(self.basic).action_verify()

    def test_verify_clears_missing_and_locks(self):
        doc = self._doc()
        doc.action_submit()
        doc.with_user(self.manager).action_verify()
        self.assertEqual(doc.state, 'verified')
        self.assertEqual(self.file.missing_count, 0)
        with self.assertRaises(UserError):
            doc.write({'number': 'CI-2'})

    def test_new_version_keeps_history(self):
        doc = self._doc()
        doc.action_submit()
        doc.with_user(self.manager).action_verify()
        res = doc.action_new_version()
        new = self.env['nelsis.commercial.document'].browse(res['res_id'])
        self.assertEqual(new.version, 2)
        self.assertEqual(doc.state, 'superseded')
        with self.assertRaises(UserError):
            doc.unlink()

    def test_duplicate_attachment_blocked(self):
        self._doc(number='CI-1', content=b'same')
        with self.assertRaises(ValidationError):
            self._doc(number='CI-9', content=b'same')

    def test_disallowed_extension(self):
        att = self._attachment(name='malware.exe', content=b'x')
        with self.assertRaises(ValidationError):
            self.env['nelsis.commercial.document'].create({
                'file_id': self.file.id, 'document_type_id': self.type_ci.id, 'number': 'X',
                'attachment_ids': [(6, 0, att.ids)]})

    def test_cannot_complete_with_missing_docs(self):
        self.file.action_submit()
        self.file.action_start_verification()
        with self.assertRaises(ValidationError):
            self.file.with_user(self.manager).action_docs_complete()

    def test_uom_category_mismatch_flagged(self):
        product = self.env['product.product'].create({'name': 'Leather', 'type': 'product'})
        uom_kg = self.env.ref('uom.product_uom_kgm')
        with self.assertRaises(ValidationError):
            self.env['nelsis.commercial.line'].create({
                'file_id': self.file.id, 'product_id': product.id, 'uom_id': uom_kg.id, 'qty': 5})

    def test_discrepancy_pending_without_receipt(self):
        product = self.env['product.product'].create({'name': 'Sole', 'type': 'product'})
        self.env['nelsis.commercial.line'].create({
            'file_id': self.file.id, 'product_id': product.id, 'uom_id': product.uom_id.id, 'qty': 10})
        self.file.action_compute_discrepancies()
        self.assertEqual(self.file.discrepancy_ids.state, 'pending')
