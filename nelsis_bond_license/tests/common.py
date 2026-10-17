# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

import itertools
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase

_counter = itertools.count(1)


class BondLicenseCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.bond_require_verified_rule = False
        cls.today = fields.Date.context_today(cls.env.user)

        def groups(*xmlids):
            return [(6, 0, [cls.env.ref(x).id for x in xmlids])]

        users = cls.env['res.users'].with_context(no_reset_password=True, mail_create_nolog=True)
        cls.user_reader = users.create({
            'name': 'Bond Reader', 'login': 'bond_reader', 'email': 'bond_reader@example.com',
            'groups_id': groups('base.group_user', 'nelsis_bond_license.group_bond_license_user')})
        cls.user_officer = users.create({
            'name': 'Bond Officer', 'login': 'bond_officer', 'email': 'bond_officer@example.com',
            'groups_id': groups('base.group_user', 'stock.group_stock_user',
                                'nelsis_bond_license.group_bond_license_officer')})
        cls.user_manager = users.create({
            'name': 'Bond Manager', 'login': 'bond_manager', 'email': 'bond_manager@example.com',
            'groups_id': groups('base.group_user', 'stock.group_stock_user',
                                'nelsis_bond_license.group_bond_license_manager')})

        cls.license_type = cls.env['bond.license.type'].create({'name': 'Test Type'})
        cls.category = cls.env['bond.factory.category'].create({'name': 'Test Category'})
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        cls.product = cls.env['product.product'].create({
            'name': 'Test Leather', 'type': 'product', 'standard_price': 10.0})
        cls.other_product = cls.env['product.product'].create({
            'name': 'Test Other Material', 'type': 'product'})

    # ------------------------------------------------------------- helpers
    def _license_vals(self, **kw):
        vals = {
            'license_number': 'LIC-%s' % next(_counter),
            'license_type_id': self.license_type.id,
            'factory_category_id': self.category.id,
            'factory_name': 'Test Factory',
            'issuing_authority': 'Test Authority',
            'customs_office': 'Test Customs Office',
            'issue_date': self.today - timedelta(days=30),
            'effective_date': self.today - timedelta(days=30),
            'expiry_date': self.today + timedelta(days=365),
            'location_ids': [(6, 0, [self.warehouse.lot_stock_id.id])],
        }
        vals.update(kw)
        return vals

    def _make_license(self, activate=True, **kw):
        lic = self.env['bond.warehouse.license'].create(self._license_vals(**kw))
        if activate:
            lic.action_activate()
        return lic

    def _make_security(self, lic, activate=True, **kw):
        vals = {
            'instrument_number': 'INS-%s' % next(_counter),
            'issuer_id': self.env['res.partner'].create({'name': 'Test Bank'}).id,
            'beneficiary_id': self.env['res.partner'].create({'name': 'Test Beneficiary'}).id,
            'license_id': lic.id,
            'amount': 1000.0,
            'issue_date': self.today - timedelta(days=10),
            'expiry_date': self.today + timedelta(days=200),
        }
        vals.update(kw)
        sec = self.env['bond.warehouse.security'].create(vals)
        if activate:
            sec.action_activate()
        return sec

    def _make_entitlement(self, lic, amount=100.0, activate=True, **kw):
        vals = {
            'reference': 'ENT-%s' % next(_counter),
            'license_id': lic.id,
            'period_from': self.today - timedelta(days=30),
            'period_to': self.today + timedelta(days=300),
            'effective_from': self.today - timedelta(days=30),
            'effective_to': self.today + timedelta(days=300),
            'product_id': self.product.id,
            'hs_code': 'TEST-HS',
            'basis': 'quantity',
            'uom_id': self.product.uom_id.id,
            'original_amount': amount,
            'approval_reference': 'APP-%s' % next(_counter),
        }
        vals.update(kw)
        ent = self.env['bond.warehouse.entitlement'].create(vals)
        if activate:
            ent.action_activate()
        return ent

    def _make_done_move(self, qty, product=None, price=10.0):
        product = product or self.product
        supplier = self.env.ref('stock.stock_location_suppliers')
        dest = self.warehouse.lot_stock_id
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': supplier.id,
            'location_dest_id': dest.id,
            'move_ids': [(0, 0, {
                'name': product.name, 'product_id': product.id, 'product_uom_qty': qty,
                'product_uom': product.uom_id.id, 'location_id': supplier.id,
                'location_dest_id': dest.id, 'price_unit': price})],
        })
        picking.action_confirm()
        picking.move_ids.write({'quantity': qty, 'picked': True})
        picking.with_context(skip_backorder=True, skip_immediate=True).button_validate()
        move = picking.move_ids
        move.write({'price_unit': price})
        return move

    def _utilize(self, ent, move, validate=True):
        util = self.env['bond.warehouse.entitlement.utilization'].create({
            'entitlement_id': ent.id, 'stock_move_id': move.id})
        if validate:
            util.action_validate()
        return util

    def _manager_action(self, record, action_code, reason='Test reason'):
        wiz = self.env['bond.warehouse.status.wizard'].with_user(self.user_manager).create({
            'res_model': record._name, 'res_id': record.id,
            'action_code': action_code, 'reason': reason})
        return wiz.action_confirm()
