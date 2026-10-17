# -*- coding: utf-8 -*-
"""Bond verification of validated receipts and period reconciliations in every status.
The store officer prepares, the bond approver (reconciliation manager) approves."""
from odoo import Command


def run(ctx):
    def verification():
        for key, outcome in (('a1', 'verified'), ('a2', 'verified'), ('c1', 'verified'),
                             ('b1', 'pending'), ('c2', 'rejected')):
            picking = ctx.u(ctx.need('receipt_' + key).picking_id, 'store')
            picking.action_bond_submit()
            manager = ctx.u(picking, 'approver')
            if outcome == 'verified':
                manager.action_bond_verify()
            elif outcome == 'rejected':
                manager.action_bond_reject()

    def new_recon(key, notes, products=(), upto='draft'):
        Recon = ctx.model_as('store', 'bond.warehouse.reconciliation')
        locations = ctx.need('loc_bond_a') | ctx.need('loc_bond_b')
        vals = {
            'date_from': ctx.d(-30), 'date_to': ctx.d(1),
            'warehouse_id': ctx.need('warehouse').id,
            'location_ids': [Command.set(locations.ids)],
            'bond_classification': 'bonded', 'notes': notes,
        }
        if products:
            vals['product_ids'] = [Command.set([ctx.need('pv_' + p).id for p in products])]
        recon = Recon.create(vals)
        ctx.reg('recon_' + key, recon)
        if upto == 'draft':
            return recon
        recon.action_compute()
        if upto in ('in_progress', 'discrepancy'):
            return recon
        for line in recon.line_ids.filtered('has_discrepancy'):
            line.write({'reason': 'Demo: difference explained by the approved cycle-count adjustment.'})
        recon.action_submit_review()
        if upto == 'review':
            return recon
        recon.action_request_approval()
        if upto == 'approval':
            return recon
        manager = ctx.u(recon, 'approver')
        manager.action_approve()
        if upto == 'reconciled':
            return recon
        manager.action_close()
        return recon

    ctx.step('recon.verification', verification)
    ctx.step('recon.draft', lambda: new_recon('draft', 'Draft reconciliation, not yet calculated.'))
    ctx.step('recon.discrepancy', lambda: new_recon(
        'discrepancy', 'Open discrepancy: unapproved adjustment on the adhesive.',
        products=['chem_pu'], upto='discrepancy'))
    ctx.step('recon.review', lambda: new_recon(
        'review', 'Waiting for the reviewer.', products=['chem_pu'], upto='review'))
    ctx.step('recon.approval', lambda: new_recon(
        'approval', 'Waiting for the approver.', products=['sole_rubber', 'trim_eyelet'], upto='approval'))
    ctx.step('recon.reconciled', lambda: new_recon(
        'reconciled', 'Leather reconciled for the period.', products=['lth_black', 'lth_tan'],
        upto='reconciled'))
    ctx.step('recon.closed', lambda: new_recon(
        'closed', 'Leather period closed.', products=['lth_black'], upto='closed'))
