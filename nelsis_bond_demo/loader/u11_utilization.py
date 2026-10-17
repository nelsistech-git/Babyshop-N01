# -*- coding: utf-8 -*-
"""Entitlement utilization against the validated receipt moves (quantity and value based)."""


def _move(ctx, receipt_key, product_key):
    picking = ctx.need('receipt_' + receipt_key).picking_id.sudo()
    product = ctx.need('pv_' + product_key)
    move = picking.move_ids.filtered(lambda m: m.product_id == product and m.state == 'done')[:1]
    if not move:
        raise ValueError('No validated move of %s on receipt %s' % (product_key, receipt_key))
    return move


def _utilize(ctx, ent_key, receipt_key, product_key, key, validate=True, note=None):
    Util = ctx.model_as('license_officer', 'bond.warehouse.entitlement.utilization')
    move = _move(ctx, receipt_key, product_key)
    util = Util.create({'entitlement_id': ctx.need('ent_' + ent_key).id, 'stock_move_id': move.id,
                        'note': note or 'Fictitious demo utilization.'})
    ctx.reg('util_' + key, util)
    if validate:
        util.action_validate()
    return util


def run(ctx):
    def leather():
        _utilize(ctx, 'lth_black', 'a1', 'lth_black', 'a1')
        _utilize(ctx, 'lth_black', 'a2', 'lth_black', 'a2')

    def chemical():
        _utilize(ctx, 'chem', 'b1', 'chem_pu', 'b1')

    def eyelet_value():
        # Receipts carry no purchase price in the demo, so give the move a fictitious unit price.
        move = _move(ctx, 'c1', 'trim_eyelet')
        ctx.env.cr.execute('UPDATE stock_move SET price_unit = %s WHERE id = %s', (0.02, move.id))
        move.invalidate_recordset(['price_unit'])
        _utilize(ctx, 'eyelet', 'c1', 'trim_eyelet', 'c1_eyelet', note='Value basis: 500,000 x 0.02 (demo price).')

    def sole():
        _utilize(ctx, 'sole', 'c1', 'sole_rubber', 'c1_sole')
        second = _utilize(ctx, 'sole', 'c2', 'sole_rubber', 'c2_sole')
        ctx.u(second, 'license_manager')._bond_apply_status(
            'reverse', 'Demo: receipt was posted against the wrong entitlement; reversed.')

    def draft_utilization():
        _utilize(ctx, 'sole', 'c2', 'sole_rubber', 'c2_sole_redo', validate=False,
                 note='Draft utilization re-raised after the reversal, waiting for validation.')

    ctx.step('utilization.leather', leather)
    ctx.step('utilization.chemical', chemical)
    ctx.step('utilization.eyelet_value', eyelet_value)
    ctx.step('utilization.sole_reversed', sole)
    ctx.step('utilization.sole_draft', draft_utilization)
