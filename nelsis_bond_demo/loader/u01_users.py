# -*- coding: utf-8 -*-
"""Persona users: one per role so maker / checker / approver are always different people."""
from odoo import Command

from .ctx import PASSWORD

# key, display name, login, extra group xml ids
PERSONAS = [
    ('compliance_officer', 'Tahmina Sultana (Compliance Officer)', 'demo_compliance_officer',
     ['nelsis_bond_compliance.group_bond_compliance_officer']),
    ('compliance_reviewer', 'Imran Hossain (Compliance Reviewer)', 'demo_compliance_reviewer',
     ['nelsis_bond_compliance.group_bond_compliance_reviewer']),
    ('compliance_approver', 'Salma Khatun (Compliance Approver)', 'demo_compliance_approver',
     ['nelsis_bond_compliance.group_bond_compliance_approver']),
    ('license_officer', 'Shirin Akter (License Officer)', 'demo_license_officer',
     ['nelsis_bond_license.group_bond_license_officer']),
    ('license_manager', 'Mahbub Alam (License Manager)', 'demo_license_manager',
     ['nelsis_bond_license.group_bond_license_manager']),
    ('lc_officer', 'Rafiq Islam (LC & Commercial Officer)', 'demo_lc_officer',
     ['nelsis_lc_management.group_lc_officer', 'nelsis_commercial.group_commercial_officer']),
    ('lc_manager', 'Nusrat Jahan (LC & Commercial Manager)', 'demo_lc_manager',
     ['nelsis_lc_management.group_lc_manager', 'nelsis_commercial.group_commercial_manager']),
    ('purchase_officer', 'Habibur Rahman (Purchase Officer)', 'demo_purchase_officer',
     ['nelsis_bond_purchase.group_bond_purchase_officer', 'uom.group_uom']),
    ('purchase_manager', 'Rokeya Begum (Purchase Manager)', 'demo_purchase_manager',
     ['nelsis_bond_purchase.group_bond_purchase_manager', 'uom.group_uom']),
    ('store', 'Jamal Uddin (Bond Store Officer)', 'demo_store',
     ['nelsis_bond_inventory.group_bond_inventory_user',
      'nelsis_bond_movement.group_bond_movement_user',
      'nelsis_bond_reconciliation.group_bond_recon_user',
      'stock.group_stock_user', 'stock.group_production_lot', 'uom.group_uom']),
    ('inspector', 'Nasrin Akter (Bond Inspector)', 'demo_inspector',
     ['nelsis_bond_inventory.group_bond_inventory_inspector',
      'stock.group_stock_user', 'stock.group_production_lot']),
    ('approver', 'Kamal Hossain (Bond Approver)', 'demo_approver',
     ['nelsis_bond_inventory.group_bond_inventory_approver',
      'nelsis_bond_movement.group_bond_movement_manager',
      'nelsis_bond_reconciliation.group_bond_recon_manager',
      'stock.group_stock_manager', 'stock.group_production_lot']),
    ('controller', 'Anwar Karim (Bond Classification Controller)', 'demo_controller',
     ['nelsis_bond_movement.group_bond_movement_controller',
      'nelsis_bond_inventory.group_bond_inventory_approver',
      'stock.group_stock_manager']),
    ('manager', 'Farhana Rahman (Bond Operations Manager)', 'demo_manager',
     ['nelsis_bond_warehouse.group_bond_suite_manager', 'stock.group_stock_manager']),
    ('auditor', 'Delwar Chowdhury (Compliance Auditor)', 'demo_auditor',
     ['nelsis_bond_warehouse.group_bond_suite_auditor']),
]


def run(ctx):
    env = ctx.env
    Users = env['res.users'].with_context(no_reset_password=True)

    def make(key, name, login, groups):
        def _create():
            user = Users.search([('login', '=', login)], limit=1)
            if not user:
                group_ids = [env.ref('base.group_user').id]
                for xmlid in groups:
                    group = env.ref(xmlid, raise_if_not_found=False)
                    if group:
                        group_ids.append(group.id)
                user = Users.create({
                    'name': name,
                    'login': login,
                    'email': '%s@demo.nelsis.example' % login,
                    'password': PASSWORD,
                    'tz': 'Asia/Dhaka',
                    'notification_type': 'inbox',
                    'company_id': ctx.company.id,
                    'company_ids': [Command.set([ctx.company.id])],
                    'groups_id': [Command.set(group_ids)],
                })
            ctx.reg('user_' + key, user)
        return _create

    for key, name, login, groups in PERSONAS:
        ctx.step('users.%s' % key, make(key, name, login, groups))
