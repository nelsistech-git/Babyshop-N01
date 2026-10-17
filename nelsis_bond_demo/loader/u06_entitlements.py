# -*- coding: utf-8 -*-
"""Entitlements (quantity and value based), amendments. Utilization comes later, once the
receipts that it points to exist."""
from .consts import LIC1
from .u05_licenses import rule_vals


def run(ctx):
    env = ctx.env

    def make(key, reference, product_key, basis, amount, uom_xmlid=None, effective=(-200, 300),
             verify=True, activate=True):
        def _do():
            Ent = ctx.model_as('license_officer', 'bond.warehouse.entitlement')
            lic = ctx.need('lic_1')
            product = ctx.need('pv_' + product_key)
            start, end = ctx.d(effective[0]), ctx.d(effective[1])
            vals = {
                'reference': reference, 'license_id': lic.id,
                'period_from': start, 'period_to': end, 'effective_from': start, 'effective_to': end,
                'product_id': product.id, 'hs_code': product.product_tmpl_id.bond_hs_code,
                'eligibility_note': 'Demo: fictitious eligibility note.',
                'basis': basis, 'original_amount': amount,
                'approval_reference': 'DEMO-APPR-%s (fictitious)' % reference,
                'approval_date': ctx.d(effective[0]),
                'note': 'Fictitious demo entitlement.',
            }
            if basis == 'quantity':
                vals['uom_id'] = product.uom_id.id
            else:
                vals['currency_id'] = ctx.company.currency_id.id
            if verify:
                vals.update(rule_vals())
            ent = Ent.create(vals)
            ctx.reg('ent_' + key, ent)
            if verify:
                ctx.u(ent, 'license_manager').action_verify_rule()
            if activate:
                ent.action_activate()
        return _do

    def expired():
        make('expired', 'DEMO-ENT-EXPIRED', 'lth_tan', 'quantity', 800.0, effective=(-400, 5))()
        ent = ctx.need('ent_expired')
        ent.with_context(bond_amendment=True).write({'effective_to': ctx.d(-30)})
        ent._bond_mark_expired()

    def closed():
        make('closed', 'DEMO-ENT-CLOSED', 'chem_pu', 'quantity', 300.0, effective=(-300, 200))()
        ctx.u(ctx.need('ent_closed'), 'license_manager')._bond_apply_status(
            'close', 'Demo: fully consumed, closed by the manager.')

    def amendments():
        Amend = ctx.model_as('license_officer', 'bond.warehouse.entitlement.amendment')
        ent = ctx.need('ent_sole')
        approved = Amend.create({
            'entitlement_id': ent.id, 'approval_reference': 'DEMO-AMD-0001 (fictitious)',
            'reason': 'Demo: approved authority amendment raising the approved quantity.',
            'change_amount': 500.0})
        ctx.u(approved, 'license_manager').action_approve()
        ctx.reg('amend_approved', approved)
        rejected = Amend.create({
            'entitlement_id': ent.id, 'approval_reference': 'DEMO-AMD-0002 (fictitious)',
            'reason': 'Demo: amendment that was rejected.', 'change_amount': 5000.0})
        ctx.u(rejected, 'license_manager')._bond_apply_status('reject', 'Demo: not supported by the authority.')
        ctx.reg('amend_rejected', rejected)
        pending = Amend.create({
            'entitlement_id': ent.id, 'approval_reference': 'DEMO-AMD-0003 (fictitious)',
            'reason': 'Demo: draft amendment waiting for the manager.', 'change_amount': 100.0})
        ctx.reg('amend_draft', pending)

    ctx.step('entitlement.leather', make('lth_black', 'DEMO-ENT-LTH-01', 'lth_black', 'quantity', 1200.0))
    ctx.step('entitlement.chemical', make('chem', 'DEMO-ENT-CHM-01', 'chem_pu', 'quantity', 2000.0))
    ctx.step('entitlement.eyelets_value', make('eyelet', 'DEMO-ENT-TRM-01', 'trim_eyelet', 'value', 50000.0))
    ctx.step('entitlement.sole', make('sole', 'DEMO-ENT-SOL-01', 'sole_rubber', 'quantity', 1000.0))
    ctx.step('entitlement.expired', expired)
    ctx.step('entitlement.draft', make('draft', 'DEMO-ENT-DRAFT', 'lth_tan', 'quantity', 500.0,
                                       verify=False, activate=False))
    ctx.step('entitlement.closed', closed)
    ctx.step('entitlement.amendments', amendments)
