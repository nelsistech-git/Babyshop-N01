# -*- coding: utf-8 -*-
"""Bond licenses (active / expiring / expired / suspended / draft), renewals and securities."""
from odoo import Command

from .consts import (LIC1, LIC2, LIC3, LIC4, LIC5, RULE_APPLICABILITY, RULE_REF, RULE_URL)

RULE_VALUES = {
    'rule_reference': RULE_REF,
    'rule_source_url': RULE_URL,
    'rule_applicability': RULE_APPLICABILITY,
    'rule_required_document': 'Demo: invented requirement text.',
}


def rule_vals():
    return dict(RULE_VALUES)


def run(ctx):
    env = ctx.env

    def masters():
        if not ctx.get('lic_type'):
            ctx.reg('lic_type', env['bond.license.type'].create({
                'name': 'Special Bonded Warehouse License (demo)', 'code': 'DEMO-SBW',
                'description': 'Fictitious license type used by the demo data.'}))
        if not ctx.get('lic_factory_cat'):
            ctx.reg('lic_factory_cat', env['bond.factory.category'].create({
                'name': 'Leather & Footwear Factory (demo)', 'code': 'DEMO-LF',
                'description': 'Fictitious factory category used by the demo data.'}))

    def new_license(key, number, issue, expiry, verify=True, activate=True, note=''):
        def _do():
            Lic = ctx.model_as('license_officer', 'bond.warehouse.license')
            vals = {
                'license_number': number,
                'license_type_id': ctx.need('lic_type').id,
                'factory_name': 'Nelsis Demo Footwear & Leather Factory (fictitious)',
                'factory_category_id': ctx.need('lic_factory_cat').id,
                'issuing_authority': 'Demo Customs Authority (fictitious)',
                'customs_office': 'Demo Customs Office (fictitious)',
                'issue_date': issue, 'effective_date': issue, 'expiry_date': expiry,
                'note': note or 'Fictitious demo license.',
            }
            if verify:
                vals.update(rule_vals())
            lic = Lic.create(vals)
            ctx.reg('lic_' + key, lic)
            att = ctx.attach(lic, 'license-%s' % number, 'Bond license copy (demo)',
                             ['License: %s' % number, 'Fictitious demo license document.'])
            lic.write({'attachment_ids': [Command.set([att.id])]})
            if verify:
                ctx.u(lic, 'license_manager').action_verify_rule()
            if activate:
                lic.action_activate()
        return _do

    def lic1():
        new_license('1', LIC1, ctx.d(-300), ctx.d(420), note='Main demo license: all bonded locations and entitlements.')()
        lic = ctx.need('lic_1')
        locations = [ctx.need(k).id for k in ('loc_bond_a', 'loc_bond_b')]
        ctx.u(lic, 'license_officer').write({'location_ids': [Command.set(locations)]})

    def lic2():
        new_license('2', LIC2, ctx.d(-700), ctx.d(25), note='Expires soon: renewal application is pending.')()
        lic = ctx.need('lic_2')
        Renewal = ctx.model_as('license_officer', 'bond.warehouse.license.renewal')
        renewal = Renewal.create({
            'license_id': lic.id, 'application_reference': 'DEMO-APP-0001 (fictitious)',
            'requested_expiry_date': ctx.d(390), 'note': 'Demo renewal application.'})
        renewal.action_submit()
        ctx.reg('renewal_pending', renewal)

    def lic3_expired():
        new_license('3', LIC3, ctx.d(-800), ctx.d(10), note='Demo license that has expired.')()
        lic = ctx.need('lic_3')
        lic.with_context(bond_renewal=True).write({'expiry_date': ctx.d(-20)})
        lic._bond_mark_expired()

    def lic4_suspended():
        new_license('4', LIC4, ctx.d(-200), ctx.d(300), note='Demo license suspended after an inspection.')()
        ctx.u(ctx.need('lic_4'), 'license_manager')._bond_apply_status(
            'suspend', 'Demo: suspended pending a customs inspection (fictitious).')

    def lic5_draft():
        new_license('5', LIC5, ctx.d(-30), ctx.d(700), verify=False, activate=False,
                    note='Draft license: regulatory basis not recorded yet.')()

    def lic6_renewed():
        new_license('6', 'DEMO-LIC-0006', ctx.d(-900), ctx.d(200), note='Demo license with an approved renewal.')()
        lic = ctx.need('lic_6')
        Renewal = ctx.model_as('license_officer', 'bond.warehouse.license.renewal')
        renewal = Renewal.create({
            'license_id': lic.id, 'application_reference': 'DEMO-APP-0002 (fictitious)',
            'requested_expiry_date': ctx.d(565)})
        renewal.action_submit()
        approver = ctx.u(renewal, 'license_manager')
        approver.write({'approval_reference': 'DEMO-APPROVAL-R2 (fictitious)'})
        approver.action_approve()
        ctx.reg('renewal_approved', renewal)

    def securities():
        Sec = ctx.model_as('license_officer', 'bond.warehouse.security')
        issuer, beneficiary = ctx.need('partner_bank_partner'), ctx.need('partner_customs_partner')

        def make(key, number, license_key, amount, issue, expiry):
            sec = Sec.create({
                'instrument_number': number, 'instrument_type': 'bank_guarantee',
                'issuer_id': issuer.id, 'beneficiary_id': beneficiary.id,
                'license_id': ctx.need('lic_' + license_key).id, 'amount': amount,
                'issue_date': issue, 'expiry_date': expiry, 'note': 'Fictitious demo guarantee.'})
            ctx.reg('sec_' + key, sec)
            sec.action_activate()
            return sec

        make('1', 'DEMO-BG-0001', '1', 250000.0, ctx.d(-250), ctx.d(300))
        make('2', 'DEMO-BG-0002', '2', 120000.0, ctx.d(-340), ctx.d(40))
        released = make('3', 'DEMO-BG-0003', '4', 80000.0, ctx.d(-180), ctx.d(100))
        ctx.u(released, 'license_manager')._bond_apply_status('release', 'Demo: released by the beneficiary.')
        old = make('4', 'DEMO-BG-0004', '1', 60000.0, ctx.d(-340), ctx.d(20))
        old.action_renew()
        renewed = old.renewed_by_ids[:1]
        renewed.write({'instrument_number': 'DEMO-BG-0004-R1', 'issue_date': ctx.d(-1),
                       'expiry_date': ctx.d(364)})
        renewed.action_activate()
        ctx.reg('sec_4_renewal', renewed)

    ctx.step('license.masters', masters)
    ctx.step('license.lic1_active', lic1)
    ctx.step('license.lic2_expiring_renewal', lic2)
    ctx.step('license.lic3_expired', lic3_expired)
    ctx.step('license.lic4_suspended', lic4_suspended)
    ctx.step('license.lic5_draft', lic5_draft)
    ctx.step('license.lic6_renewed', lic6_renewed)
    ctx.step('license.securities', securities)
