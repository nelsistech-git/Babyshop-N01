# -*- coding: utf-8 -*-
"""Bond movements through the maker-checker workflow: the store officer prepares, the bond
approver approves and validates.

Only movements the suite itself allows are created: bonded transfers, bonded issues to the
consumption location, negative bonded adjustments, and non-bonded issues with a return.
(The suite's stock guard blocks bonded returns and positive bonded adjustments.)"""
from odoo import Command

from .consts import BOE_A, BOE_B, LC_A, LC_B, LIC1


def _lot(ctx, name, product_key):
    lot = ctx.env['stock.lot'].sudo().search(
        [('name', '=', name), ('product_id', '=', ctx.need('pv_' + product_key).id)], limit=1)
    if not lot:
        raise ValueError('Lot %s not found' % name)
    return lot


def new_movement(ctx, key, mtype, product_key, qty, src_key, dst_key=None, lot=None,
                 upto='done', refs=None, **extra):
    Mov = ctx.model_as('store', 'bond.warehouse.movement')
    product = ctx.need('pv_' + product_key)
    vals = {
        'movement_type': mtype, 'product_id': product.id, 'quantity': qty,
        'location_id': ctx.need(src_key).id, 'date': ctx.env.cr.now(),
        'reason': extra.pop('reason', 'Fictitious demo %s.' % mtype),
    }
    if dst_key == 'consumption':
        vals['location_dest_id'] = ctx.env.ref('nelsis_bond_movement.location_bond_consumption').id
    elif dst_key:
        vals['location_dest_id'] = ctx.need(dst_key).id
    if lot:
        vals['lot_id'] = lot.id
    vals.update(refs or {})
    vals.update(extra)
    mov = Mov.create(vals)
    ctx.reg('mov_' + key, mov)
    if upto == 'draft':
        return mov
    if upto == 'cancelled':
        mov.action_cancel()
        return mov
    mov.action_submit()
    if upto == 'submitted':
        return mov
    approver = ctx.u(mov, 'approver')
    approver.action_approve()
    if upto == 'approved':
        return mov
    approver.action_validate()
    return mov


BOND_A = {'license_ref': LIC1, 'lc_ref': LC_A, 'boe_ref': BOE_A}
BOND_B = {'license_ref': LIC1, 'lc_ref': LC_B, 'boe_ref': BOE_B}


def run(ctx):
    def prepare_locations():
        for key in ('loc_bond_a_leather', 'loc_bond_a_chem', 'loc_bond_a', 'loc_bond_b', 'loc_nonbond'):
            loc = ctx.need(key)
            if 'bond_movement_allowed' in loc._fields and not loc.bond_movement_allowed:
                loc.sudo().write({'bond_movement_allowed': True})
        nb = ctx.need('loc_nonbond')
        if nb.bond_classification != 'non_bonded':
            # Same context key the suite core uses when it syncs the classification itself.
            nb.sudo().with_context(bond_suite_sync=True).write({'bond_classification': 'non_bonded'})

    def transfers():
        lot = _lot(ctx, 'DEMO-LB-2601', 'lth_black')
        new_movement(ctx, 'transfer_done', 'transfer', 'lth_black', 100.0, 'loc_bond_a_leather',
                     'loc_bond_b', lot, refs=BOND_A, reason='Demo: move leather to the second bonded store.')
        rev = new_movement(ctx, 'transfer_reversed', 'transfer', 'lth_black', 50.0, 'loc_bond_a_leather',
                           'loc_bond_b', lot, refs=BOND_A, reason='Demo: transfer posted by mistake.')
        ctx.u(rev, 'approver').action_reverse('Demo: wrong destination store, reversed.')
        new_movement(ctx, 'transfer_submitted', 'transfer', 'lth_black', 20.0, 'loc_bond_a_leather',
                     'loc_bond_b', lot, upto='submitted', refs=BOND_A)
        new_movement(ctx, 'transfer_approved', 'transfer', 'lth_black', 10.0, 'loc_bond_a_leather',
                     'loc_bond_b', lot, upto='approved', refs=BOND_A)
        new_movement(ctx, 'transfer_cancelled', 'transfer', 'lth_black', 5.0, 'loc_bond_a_leather',
                     'loc_bond_b', lot, upto='cancelled', refs=BOND_A)

    def issues():
        lot = _lot(ctx, 'DEMO-LB-2601', 'lth_black')
        new_movement(ctx, 'issue_done', 'issue', 'lth_black', 150.0, 'loc_bond_a_leather', 'consumption', lot,
                     refs=BOND_A, operational_ref='DEMO-WO-0001', recipient_ref='Cutting Department (demo)',
                     support_approval_ref='DEMO-MRQ-0001', reason='Demo: leather issued to production.')
        pu = _lot(ctx, 'DEMO-PU-2601', 'chem_pu')
        new_movement(ctx, 'issue_chem', 'issue', 'chem_pu', 200.0, 'loc_bond_a_chem', 'consumption', pu,
                     refs=BOND_B, operational_ref='DEMO-WO-0002', recipient_ref='Lasting Department (demo)',
                     support_approval_ref='DEMO-MRQ-0002', reason='Demo: adhesive issued to production.')
        new_movement(ctx, 'issue_draft', 'issue', 'lth_black', 30.0, 'loc_bond_a_leather', 'consumption',
                     lot, upto='draft', refs=BOND_A, operational_ref='DEMO-WO-0003',
                     recipient_ref='Cutting Department (demo)', support_approval_ref='DEMO-MRQ-0003')

    def _adjustment(key, product_key, lot_name, loc_key, shortage, refs, approve):
        lot = _lot(ctx, lot_name, product_key)
        Mov = ctx.model_as('store', 'bond.warehouse.movement')
        loc = ctx.need(loc_key)
        probe = Mov.create({
            'movement_type': 'adjustment', 'product_id': ctx.need('pv_' + product_key).id,
            'lot_id': lot.id, 'location_id': loc.id, 'date': ctx.env.cr.now(),
            'reason': 'Demo: cycle count shortage.', 'count_ref': 'DEMO-COUNT-%s' % key.upper(), **refs})
        onhand = probe.sudo()._get_onhand()
        probe.write({'counted_qty': onhand - shortage})
        att = ctx.attach(probe, 'count-sheet-%s' % key, 'Physical count sheet (demo)',
                         ['Count reference: DEMO-COUNT-%s' % key.upper()])
        probe.write({'evidence_ids': [Command.set([att.id])]})
        ctx.reg('mov_adj_' + key, probe)
        probe.action_submit()
        approver = ctx.u(probe, 'approver')
        approver.action_approve()
        approver.action_validate()
        if approve:
            lines = probe.sudo().move_id.move_line_ids
            ctx.u(lines, 'approver').action_bond_approve_adjustment()

    def adjustments():
        _adjustment('tan', 'lth_tan', 'DEMO-LT-2601', 'loc_bond_a_leather', 3.0, BOND_A, approve=True)

    def adjustment_unapproved():
        _adjustment('pu', 'chem_pu', 'DEMO-PU-2601', 'loc_bond_a_chem', 10.0, BOND_B, approve=False)

    def nonbonded():
        issue = new_movement(ctx, 'nb_issue', 'issue', 'carton', 500.0, 'loc_nonbond', 'consumption',
                             bond_classification='non_bonded', operational_ref='DEMO-WO-0004',
                             recipient_ref='Packing Department (demo)', support_approval_ref='DEMO-MRQ-0004',
                             reason='Demo: cartons issued to packing.')
        Mov = ctx.model_as('store', 'bond.warehouse.movement')
        ret = Mov.create({
            'movement_type': 'return', 'product_id': ctx.need('pv_carton').id, 'quantity': 100.0,
            'bond_classification': 'non_bonded', 'origin_issue_id': issue.id,
            'location_id': ctx.env.ref('nelsis_bond_movement.location_bond_consumption').id,
            'location_dest_id': ctx.need('loc_nonbond').id, 'date': ctx.env.cr.now(),
            'return_condition': 'good', 'inspection_result': 'Demo: cartons undamaged, reusable.',
            'reason': 'Demo: unused cartons returned from packing.'})
        ctx.reg('mov_nb_return', ret)
        ret.action_submit()
        approver = ctx.u(ret, 'approver')
        approver.action_approve()
        approver.action_validate()

    ctx.step('movements.prepare_locations', prepare_locations)
    ctx.step('movements.transfers', transfers)
    ctx.step('movements.issues', issues)
    ctx.step('movements.adjustment_approved', adjustments)
    ctx.step('movements.adjustment_unapproved', adjustment_unapproved)
    ctx.step('movements.nonbonded_issue_return', nonbonded)
