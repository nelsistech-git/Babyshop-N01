# -*- coding: utf-8 -*-
"""Consignments and bonded / non-bonded receipts through the real receipt workflow:
store officer prepares, inspector verifies and inspects, approver approves, store validates."""
from odoo import Command

from .consts import (BOE_A, BOE_B, BOE_C, LC_A, LC_B, LC_C, LIC1)
from .ctx import create_optional

INV = 'nelsis_bond_inventory.'
DOC_SET = [('doc_type_lc_copy', 'LC copy'), ('doc_type_bill_of_entry', 'Bill of Entry copy'),
           ('doc_type_invoice', 'Commercial invoice')]


def make_consignment(ctx, key, supplier_key, lc_key, lc_number, boe, lines, open_it=True):
    """lines: list of (line key, product key, declared qty)."""
    Cons = ctx.model_as('store', 'bond.inventory.consignment')
    vals = {
        'partner_id': ctx.need('partner_' + supplier_key).id,
        'lc_number': lc_number, 'boe_number': boe, 'boe_date': ctx.d(-20),
        'note': 'Fictitious demo consignment.',
        'line_ids': [Command.create({'product_id': ctx.need('pv_' + p).id, 'declared_qty': qty})
                     for _lk, p, qty in lines],
    }
    optional = {}
    lc = ctx.get('lc_' + lc_key) if lc_key else None
    if lc:
        optional['lc_ref'] = 'nelsis.lc,%d' % lc.id
    cons = create_optional(Cons, vals, optional)
    ctx.reg('cons_' + key, cons)
    for (line_key, _p, _q), line in zip(lines, cons.line_ids):
        ctx.reg('consline_%s_%s' % (key, line_key), line)
    if open_it:
        cons.action_open()
    return cons


def make_receipt(ctx, key, lines, location_key, upto='done', cons_key=None, supplier_key=None,
                 bond_status='bonded', header=None, with_docs=True):
    """lines: list of dicts: consline (line key) or product, declared, received, damaged, rejected,
    lot, expiry, note."""
    Receipt = ctx.model_as('store', 'bond.inventory.receipt')
    cons = ctx.get('cons_' + cons_key) if cons_key else None
    vals = {
        'bond_status': bond_status,
        'partner_id': (cons.partner_id.id if cons else ctx.need('partner_' + supplier_key).id),
        'location_dest_id': ctx.need(location_key).id,
        'note': 'Fictitious demo receipt.',
    }
    if cons:
        vals['consignment_id'] = cons.id
        vals.update({'lc_number': cons.lc_number, 'boe_number': cons.boe_number,
                     'boe_date': cons.boe_date})
    vals.update(header or {})
    line_vals = []
    for spec in lines:
        lv = {'declared_qty': spec['declared']}
        if spec.get('consline'):
            cl = ctx.need('consline_%s_%s' % (cons_key, spec['consline']))
            lv.update({'consignment_line_id': cl.id, 'product_id': cl.product_id.id})
        else:
            lv['product_id'] = ctx.need('pv_' + spec['product']).id
        line_vals.append(Command.create(lv))
    vals['line_ids'] = line_vals
    receipt = Receipt.create(vals)
    ctx.reg('receipt_' + key, receipt)
    if upto == 'draft':
        return receipt
    if upto == 'cancelled':
        receipt.action_cancel()
        return receipt

    receipt.action_submit_verification()
    inspector = ctx.u(receipt, 'inspector')
    if bond_status == 'bonded' and with_docs:
        Doc = ctx.model_as('store', 'bond.inventory.receipt.document')
        for xml, label in DOC_SET:
            doc = Doc.create({
                'receipt_id': receipt.id, 'type_id': ctx.env.ref(INV + xml).id,
                'reference': 'DEMO-%s-%s' % (xml[9:].upper(), receipt.name),
                'document_date': ctx.d(-25)})
            att = ctx.attach(doc, 'receipt-%s-%s' % (key, xml[9:]), label + ' (demo)',
                             ['Receipt: %s' % receipt.name])
            doc.write({'attachment_ids': [Command.set([att.id])]})
    if upto == 'doc_verification':
        return receipt
    if bond_status == 'bonded' and with_docs:
        for doc in inspector.document_ids:
            doc.action_verify()
    if upto == 'rejected':
        inspector.write({'reject_reason': 'Demo: documents do not match the goods delivered.'})
        inspector.action_reject()
        return receipt
    inspector.action_verify_documents()

    for spec, line in zip(lines, inspector.line_ids):
        vals = {'received_qty': spec['received'], 'damaged_qty': spec.get('damaged', 0.0),
                'rejected_qty': spec.get('rejected', 0.0)}
        if spec.get('lot'):
            vals['lot_name'] = spec['lot']
        if spec.get('expiry'):
            vals['expiry_date'] = spec['expiry']
        if spec.get('note'):
            vals['disposition_note'] = spec['note']
        line.write(vals)
    if upto == 'inspection':
        return receipt
    inspector.action_mark_all_inspected()
    inspector.action_complete_inspection()
    if upto == 'approval':
        return receipt
    if receipt.state == 'approval':
        ctx.u(receipt, 'approver').action_approve()
    if upto == 'ready':
        return receipt
    receipt.action_validate()
    return receipt


def finalize(ctx, receipt, lc_number, boe, entitlement_ref=False):
    """Bond references on the validated transfer (used by the register and reconciliation)."""
    picking = receipt.picking_id.sudo()
    picking.write({'bond_license_ref': LIC1, 'bond_lc_ref': lc_number, 'bond_boe_ref': boe,
                   'bond_entitlement_ref': entitlement_ref or False})
    picking._bond_propagate_refs_to_lots()
    return picking


def run(ctx):
    d = ctx.d

    def cons_a():
        make_consignment(ctx, 'a', 'sup_leather', 'a', LC_A, BOE_A, [
            ('black', 'lth_black', 1000.0), ('tan', 'lth_tan', 600.0)])

    def receipts_a():
        r1 = make_receipt(ctx, 'a1', [
            {'consline': 'black', 'declared': 600.0, 'received': 590.0, 'lot': 'DEMO-LB-2601',
             'note': 'Short delivery of 10 sqm recorded.'},
            {'consline': 'tan', 'declared': 600.0, 'received': 600.0, 'damaged': 5.0, 'lot': 'DEMO-LT-2601',
             'note': '5 sqm damaged in transit, set aside.'},
        ], 'loc_bond_a_leather', cons_key='a')
        finalize(ctx, r1, LC_A, BOE_A, 'DEMO-ENT-LTH-01')
        r2 = make_receipt(ctx, 'a2', [
            {'consline': 'black', 'declared': 400.0, 'received': 400.0, 'lot': 'DEMO-LB-2602'},
        ], 'loc_bond_a_leather', cons_key='a')
        finalize(ctx, r2, LC_A, BOE_A, 'DEMO-ENT-LTH-01')
        ctx.u(ctx.need('cons_a'), 'store').action_close()

    def cons_b():
        make_consignment(ctx, 'b', 'sup_chem', 'b', LC_B, BOE_B, [('pu', 'chem_pu', 2500.0)])

    def receipts_b():
        r3 = make_receipt(ctx, 'b1', [
            {'consline': 'pu', 'declared': 1700.0, 'received': 1700.0, 'lot': 'DEMO-PU-2601',
             'expiry': d(240)},
        ], 'loc_bond_a_chem', cons_key='b')
        finalize(ctx, r3, LC_B, BOE_B, 'DEMO-ENT-CHM-01')
        make_receipt(ctx, 'b2', [
            {'consline': 'pu', 'declared': 500.0, 'received': 480.0, 'lot': 'DEMO-PU-2602',
             'expiry': d(200), 'note': 'Shortage of 20 kg recorded.'},
        ], 'loc_bond_a_chem', cons_key='b', upto='approval')
        make_receipt(ctx, 'b3', [
            {'consline': 'pu', 'declared': 300.0, 'received': 300.0, 'lot': 'DEMO-PU-2603',
             'expiry': d(210)},
        ], 'loc_bond_a_chem', cons_key='b', upto='inspection')

    def cons_c():
        make_consignment(ctx, 'c', 'sup_trim', 'c', LC_C, BOE_C, [
            ('eyelet', 'trim_eyelet', 500000.0), ('sole', 'sole_rubber', 1500.0)])

    def receipts_c():
        r7 = make_receipt(ctx, 'c1', [
            {'consline': 'eyelet', 'declared': 500000.0, 'received': 500000.0, 'lot': 'DEMO-EY-2601'},
            {'consline': 'sole', 'declared': 400.0, 'received': 400.0, 'lot': 'DEMO-SR-2601'},
        ], 'loc_bond_a', cons_key='c')
        finalize(ctx, r7, LC_C, BOE_C, 'DEMO-ENT-TRM-01')
        r8 = make_receipt(ctx, 'c2', [
            {'consline': 'sole', 'declared': 800.0, 'received': 800.0, 'lot': 'DEMO-SR-2602'},
        ], 'loc_bond_b', cons_key='c')
        finalize(ctx, r8, LC_C, BOE_C, 'DEMO-ENT-SOL-01')
        make_receipt(ctx, 'c3', [
            {'consline': 'sole', 'declared': 300.0, 'received': 300.0, 'lot': 'DEMO-SR-2603'},
        ], 'loc_bond_b', cons_key='c', upto='rejected')

    def other_receipts():
        make_receipt(ctx, 'draft', [{'product': 'trim_eyelet', 'declared': 20000.0}],
                     'loc_bond_a', supplier_key='sup_trim', upto='draft',
                     header={'lc_number': 'DEMO-LC-0006', 'boe_number': 'DEMO-BOE-0006'})
        make_receipt(ctx, 'cancelled', [{'product': 'lth_black', 'declared': 50.0}],
                     'loc_bond_a_leather', supplier_key='sup_leather', upto='cancelled',
                     header={'lc_number': 'DEMO-LC-0006', 'boe_number': 'DEMO-BOE-0007'})
        make_receipt(ctx, 'docs', [{'product': 'lth_tan', 'declared': 250.0}],
                     'loc_bond_a_leather', supplier_key='sup_leather', upto='doc_verification',
                     header={'lc_number': 'DEMO-LC-0007', 'boe_number': 'DEMO-BOE-0008'})
        rn = make_receipt(ctx, 'nonbonded', [
            {'product': 'carton', 'declared': 3000.0, 'received': 3000.0}],
            'loc_nonbond', supplier_key='sup_local', bond_status='non_bonded')
        return rn

    def consignment_states():
        make_consignment(ctx, 'draft', 'sup_leather', None, 'DEMO-LC-0004', 'DEMO-BOE-0004',
                         [('black', 'lth_black', 300.0)], open_it=False)
        cancelled = make_consignment(ctx, 'cancelled', 'sup_chem', None, 'DEMO-LC-0005', 'DEMO-BOE-0005',
                                     [('pu', 'chem_pu', 100.0)])
        cancelled.action_cancel()

    ctx.step('receipts.consignment_a', cons_a)
    ctx.step('receipts.receipts_a', receipts_a)
    ctx.step('receipts.consignment_b', cons_b)
    ctx.step('receipts.receipts_b', receipts_b)
    ctx.step('receipts.consignment_c', cons_c)
    ctx.step('receipts.receipts_c', receipts_c)
    ctx.step('receipts.other_receipts', other_receipts)
    ctx.step('receipts.consignment_states', consignment_states)
