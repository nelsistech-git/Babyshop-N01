# -*- coding: utf-8 -*-
"""Bond classification: locations and products become bonded only through approved,
evidenced classification requests (store officer requests, approver decides)."""
from odoo import Command

from .consts import LIC1

BONDED_PRODUCTS = ['lth_black', 'lth_tan', 'chem_pu', 'trim_eyelet', 'sole_rubber']
CHILD_LOCATIONS = [('loc_bond_a_leather', 'Leather Rack'), ('loc_bond_a_chem', 'Chemical Cage')]


def _request(ctx, key, vals, evidence_title, submit=True, approve=False, reject_reason=None):
    """Create a request as the store officer, optionally submit and decide it."""
    Req = ctx.model_as('store', 'bond.inventory.classification.request')
    req = Req.create(dict(vals, reason=vals.get('reason') or 'Demo classification request (fictitious).'))
    ctx.reg(key, req)
    if submit:
        att = ctx.attach(req, 'evidence-%s' % key, evidence_title,
                         ['Request: %s' % req.name, 'Supporting evidence for demo classification.'])
        req.write({'attachment_ids': [Command.set([att.id])]})
        req.action_submit()
    if approve:
        ctx.u(req, 'approver').action_approve()
    elif reject_reason:
        approver_req = ctx.u(req, 'approver')
        approver_req.write({'rejection_reason': reject_reason})
        approver_req.action_reject()
    return req


def run(ctx):
    env = ctx.env

    def bond_location(key):
        def _do():
            loc = ctx.need(key)
            _request(ctx, 'creq_' + key, {
                'target_type': 'location', 'location_id': loc.id, 'new_status': 'bonded',
                'license_ref': LIC1, 'authorized_from': ctx.d(-300), 'authorized_to': ctx.d(420),
                'reason': 'Demo: location authorised under fictitious license %s.' % LIC1,
            }, 'Bond license copy (demo)', approve=True)
        return _do

    def child_locations():
        parent = ctx.need('loc_bond_a')
        for key, name in CHILD_LOCATIONS:
            if ctx.get(key):
                continue
            child = env['stock.location'].create({
                'name': name, 'usage': 'internal', 'location_id': parent.id,
                'company_id': ctx.company.id,
            })
            child.write({'bond_movement_allowed': True})
            ctx.reg(key, child)

    def bond_product(key):
        def _do():
            tmpl = ctx.need('prod_' + key)
            _request(ctx, 'creq_prod_' + key, {
                'target_type': 'product', 'product_tmpl_id': tmpl.id, 'new_status': 'bonded',
                'reason': 'Demo: raw material eligible for the bonded store.',
            }, 'Eligibility evidence (demo)', approve=True)
        return _do

    def pending_requests():
        _request(ctx, 'creq_prod_lth_suede', {
            'target_type': 'product', 'product_tmpl_id': ctx.need('prod_lth_suede').id,
            'new_status': 'bonded', 'reason': 'Demo: waiting for the approver.',
        }, 'Eligibility evidence (demo)')
        _request(ctx, 'creq_prod_carton', {
            'target_type': 'product', 'product_tmpl_id': ctx.need('prod_carton').id,
            'new_status': 'bonded', 'reason': 'Demo: local packaging requested as bonded by mistake.',
        }, 'Eligibility evidence (demo)',
            reject_reason='Local packaging is not imported under bond. Request rejected (demo).')
        _request(ctx, 'creq_draft', {
            'target_type': 'location', 'location_id': ctx.need('loc_nonbond').id,
            'new_status': 'bonded', 'license_ref': 'DEMO-LIC-DRAFT',
            'reason': 'Demo: draft request that was never submitted.',
        }, 'n/a', submit=False)

    ctx.step('class.loc_bond_a', bond_location('loc_bond_a'))
    ctx.step('class.loc_bond_b', bond_location('loc_bond_b'))
    ctx.step('class.child_locations', child_locations)
    for key in BONDED_PRODUCTS:
        ctx.step('class.prod_%s' % key, bond_product(key))
    ctx.step('class.pending_requests', pending_requests)
