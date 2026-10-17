# -*- coding: utf-8 -*-
"""Purchase orders (nelsis_bond_purchase) wired to the LCs, consignments and receipts above.
Everything runs through the real workflow as the purchase / store personas."""
from odoo import Command

from .u08_receipts import make_receipt

BOE_P1 = 'DEMO-BOE-0010'


def _order(ctx, key, supplier_key, kind, lines, lc_key=None, ent_key=None, confirm=True, ref=None):
    """lines: (product key, qty, unit price). Created and confirmed by the purchase officer."""
    PO = ctx.model_as('purchase_officer', 'purchase.order')
    vals = {
        'partner_id': ctx.need('partner_' + supplier_key).id,
        'bond_purchase_type': kind,
        'partner_ref': ref or 'DEMO-PI-%s' % key.upper(),
        'order_line': [Command.create({
            'product_id': ctx.need('pv_' + p).id, 'name': ctx.need('pv_' + p).display_name,
            'product_qty': qty, 'price_unit': price, 'date_planned': ctx.d(30),
            'taxes_id': [Command.clear()]}) for p, qty, price in lines],
    }
    if lc_key:
        vals['lc_id'] = ctx.need('lc_' + lc_key).id
    if ent_key:
        vals['bond_entitlement_id'] = ctx.need('ent_' + ent_key).id
    po = PO.create(vals)
    ctx.reg('po_' + key, po)
    if confirm:
        po.button_confirm()
    return po


def _consignment(ctx, key, po, boe):
    """Consignment created from the order (officer), Bill of Entry added and opened by the store."""
    action = ctx.u(po, 'purchase_officer').action_bond_create_consignment()
    cons = ctx.env['bond.inventory.consignment'].browse(action['res_id'])
    ctx.reg('cons_' + key, cons)
    for line in cons.line_ids:
        pk = line.product_id.default_code
        ctx.reg('consline_%s_%s' % (key, {'DEMO-LTH-001': 'black', 'DEMO-LTH-002': 'tan'}.get(pk, pk)), line)
    store = ctx.u(cons, 'store')
    store.write({'boe_number': boe, 'boe_date': ctx.d(-5)})
    store.action_open()
    return cons


def run(ctx):
    def p1_order():
        _order(ctx, 'p1', 'sup_leather', 'import_bonded',
               [('lth_black', 200.0, 7.0), ('lth_tan', 100.0, 10.0)], lc_key='i', ent_key='lth_black')

    def p1_consignment():
        _consignment(ctx, 'p1', ctx.need('po_p1'), BOE_P1)

    def p1_receipts():
        make_receipt(ctx, 'p1a', [{'consline': 'black', 'declared': 120.0, 'received': 120.0,
                                   'lot': 'DEMO-LB-P101'}], 'loc_bond_a_leather', cons_key='p1')
        make_receipt(ctx, 'p1b', [{'consline': 'black', 'declared': 80.0, 'received': 80.0,
                                   'lot': 'DEMO-LB-P102'}], 'loc_bond_a_leather', cons_key='p1',
                     upto='approval')

    def p1_commercial():
        po = ctx.need('po_p1')
        ctx.u(po, 'purchase_officer').action_bond_create_commercial_file()
        ctx.u(po, 'purchase_officer').action_bond_sync()

    def p2_order():
        _order(ctx, 'p2', 'sup_trim', 'import_bonded',
               [('trim_eyelet', 300000.0, 0.02), ('sole_rubber', 500.0, 3.10)], lc_key='f')

    def p3_local():
        po = _order(ctx, 'p3', 'sup_local', 'local', [('carton', 2000.0, 0.45)])
        picking = ctx.u(po.picking_ids[:1], 'store')
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.button_validate()

    def p4_rfq():
        _order(ctx, 'p4', 'sup_chem', 'import_bonded', [('chem_pu', 1000.0, 4.2)], lc_key='e', confirm=False)

    def p5_cancelled():
        po = _order(ctx, 'p5', 'sup_local', 'local', [('carton', 500.0, 0.45)], confirm=False)
        po.button_cancel()

    def retro(key, supplier_key, lc_key, lines, cons_key):
        po = _order(ctx, key, supplier_key, 'import_bonded', lines, lc_key=lc_key)
        ctx.need('cons_' + cons_key).write({'purchase_order_id': po.id})
        ctx.u(po, 'purchase_officer').action_bond_sync()

    def p6_retro():
        retro('p6', 'sup_chem', 'b', [('chem_pu', 2500.0, 4.2)], 'b')

    def p7_retro():
        retro('p7', 'sup_trim', 'c', [('trim_eyelet', 500000.0, 0.02), ('sole_rubber', 1500.0, 3.10)], 'c')

    ctx.step('purchase.p1_order', p1_order)
    ctx.step('purchase.p1_consignment', p1_consignment)
    ctx.step('purchase.p1_receipts', p1_receipts)
    ctx.step('purchase.p1_commercial_file', p1_commercial)
    ctx.step('purchase.p2_order', p2_order)
    ctx.step('purchase.p3_local', p3_local)
    ctx.step('purchase.p4_rfq', p4_rfq)
    ctx.step('purchase.p5_cancelled', p5_cancelled)
    ctx.step('purchase.p6_retro_link', p6_retro)
    ctx.step('purchase.p7_retro_link', p7_retro)
