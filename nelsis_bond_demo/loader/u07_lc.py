# -*- coding: utf-8 -*-
"""Letters of Credit in every lifecycle state, with shipments, Bills of Entry,
document checklists and amendments (officer prepares, manager approves)."""
from .consts import BOE_A, BOE_B, BOE_C, LC_A, LC_B, LC_C, LIC1

LC_NS = 'nelsis_lc_management.'


def _doc_type(ctx, suffix):
    return ctx.env.ref(LC_NS + 'doctype_' + suffix)


def new_lc(ctx, key, number, supplier_key, amount, state='opened', purpose='raw_material',
           opening=-120, expiry=120, deadline=60, tolerance=5.0, note=''):
    """Create an LC as the officer and move it to ``state`` through the real workflow."""
    LC = ctx.model_as('lc_officer', 'nelsis.lc')
    lc = LC.create({
        'lc_number': number, 'lc_type': 'import', 'purpose': purpose,
        'partner_id': ctx.need('partner_' + supplier_key).id,
        'bank_id': ctx.need('bank_demo').id, 'bank_branch': 'Demo Main Branch (fictitious)',
        'currency_id': ctx.company.currency_id.id, 'original_amount': amount,
        'opening_date': ctx.d(opening), 'expiry_date': ctx.d(expiry),
        'shipment_deadline': ctx.d(deadline), 'tolerance_percent': tolerance,
        'port_loading': 'Demo Port of Loading', 'port_discharge': 'Demo Port of Discharge',
        'incoterm': 'CIF', 'pi_number': 'PI-%s' % number, 'pi_date': ctx.d(opening - 10),
        'bond_license_ref': LIC1, 'department': 'Import & Bond',
        'payment_term': 'sight', 'note': '<p>%s</p>' % (note or 'Fictitious demo LC.'),
    })
    ctx.reg('lc_' + key, lc)
    if state == 'draft':
        return lc
    lc.action_submit()
    if state == 'review':
        return lc
    manager = ctx.u(lc, 'lc_manager')
    manager.action_approve()
    if state == 'approved':
        return lc
    lc.action_open()
    return lc


def new_shipment(ctx, lc, key, value, ship_days, eta_days, upto='planned', boe=None, invoice=None):
    """Create a shipment and advance it (planned -> shipped -> docs -> cleared)."""
    Shipment = ctx.model_as('lc_officer', 'nelsis.lc.shipment')
    sh = Shipment.create({
        'lc_id': lc.id, 'bl_awb_no': 'DEMO-BL-%s' % key.upper(), 'vessel': 'MV Demo Voyager',
        'invoice_no': invoice or 'DEMO-INV-%s' % key.upper(), 'invoice_date': ctx.d(ship_days - 3),
        'invoice_value': value, 'shipment_date': ctx.d(ship_days), 'eta_date': ctx.d(eta_days),
    })
    ctx.reg('shp_' + key, sh)
    steps = ['planned', 'shipped', 'docs_received', 'customs_cleared']
    if steps.index(upto) >= 1:
        sh.action_ship()
    if steps.index(upto) >= 2:
        sh.action_docs_received()
    if steps.index(upto) >= 3:
        Boe = ctx.model_as('lc_officer', 'nelsis.lc.boe')
        b = Boe.create({
            'name': boe, 'lc_id': lc.id, 'shipment_id': sh.id, 'boe_date': ctx.d(eta_days + 1),
            'customs_house': 'Demo Customs Station (fictitious)',
            'assessed_value': value * 100.0, 'duty_paid_amount': 0.0,
            'clearance_date': ctx.d(eta_days + 4),
            'note': 'Fictitious demo Bill of Entry. Duty figures are not computed.',
        })
        ctx.reg('boe_' + key, b)
        b.action_submit()
        b.action_clear()
        sh.action_clear()
    return sh


def add_documents(ctx, lc, shipment, suffixes, received=True):
    Doc = ctx.model_as('lc_officer', 'nelsis.lc.document')
    for suffix in suffixes:
        doc = Doc.create({
            'lc_id': lc.id, 'shipment_id': shipment.id if shipment else False,
            'type_id': _doc_type(ctx, suffix).id, 'is_required': True,
            'name': 'DEMO-%s-%s' % (suffix.upper(), lc.lc_number), 'due_date': ctx.d(10),
        })
        if received:
            doc.action_mark_received()


def run(ctx):
    def lc_a():
        lc = new_lc(ctx, 'a', LC_A, 'sup_leather', 120000.0, note='Imported finished leather (fully received).')
        s1 = new_shipment(ctx, lc, 'a1', 70000.0, -90, -75, upto='customs_cleared', boe=BOE_A, invoice='DEMO-INV-A1')
        add_documents(ctx, lc, s1, ['commercial_invoice', 'packing_list', 'bl_awb'])
        new_shipment(ctx, lc, 'a2', 45000.0, -60, -45, upto='customs_cleared', boe=BOE_A + '-2', invoice='DEMO-INV-A2')

    def lc_b():
        lc = new_lc(ctx, 'b', LC_B, 'sup_chem', 60000.0, purpose='raw_material',
                    note='Imported adhesive: one shipment received, one in transit.')
        new_shipment(ctx, lc, 'b1', 30000.0, -50, -35, upto='customs_cleared', boe=BOE_B, invoice='DEMO-INV-B1')
        new_shipment(ctx, lc, 'b2', 25000.0, -5, 20, upto='shipped', invoice='DEMO-INV-B2')

    def lc_c():
        lc = new_lc(ctx, 'c', LC_C, 'sup_trim', 45000.0, purpose='packing',
                    note='Imported trims and sole compound.')
        new_shipment(ctx, lc, 'c1', 38000.0, -40, -28, upto='customs_cleared', boe=BOE_C, invoice='DEMO-INV-C1')

    def lc_states():
        new_lc(ctx, 'd', 'DEMO-LC-0004', 'sup_leather', 30000.0, state='draft', note='Draft LC.')
        new_lc(ctx, 'e', 'DEMO-LC-0005', 'sup_chem', 22000.0, state='review', note='LC waiting for approval.')
        new_lc(ctx, 'f', 'DEMO-LC-0006', 'sup_trim', 18000.0, state='approved',
               opening=-3, note='Approved LC, not yet opened with the bank.')
        hold = new_lc(ctx, 'g', 'DEMO-LC-0007', 'sup_leather', 52000.0, note='LC on hold (document dispute).')
        ctx.u(hold, 'lc_officer')._do_hold('Demo: supplier documents under dispute.')
        cancelled = new_lc(ctx, 'h', 'DEMO-LC-0008', 'sup_chem', 15000.0, state='draft',
                           note='LC cancelled before submission.')
        ctx.u(cancelled, 'lc_officer')._do_cancel('Demo: order cancelled by purchasing.')

    def lc_amendments():
        lc = new_lc(ctx, 'i', 'DEMO-LC-0009', 'sup_leather', 80000.0, note='LC with amendments.')
        Amend = ctx.model_as('lc_officer', 'nelsis.lc.amendment')
        approved = Amend.create({
            'lc_id': lc.id, 'bank_reference': 'DEMO-SWIFT-0001', 'amount_change': 10000.0,
            'new_expiry_date': ctx.d(150), 'reason': 'Demo: price increase and extended validity.'})
        approved.action_submit()
        ctx.u(approved, 'lc_manager').action_approve()
        ctx.reg('lcamd_approved', approved)
        pending = Amend.create({
            'lc_id': lc.id, 'bank_reference': 'DEMO-SWIFT-0002', 'amount_change': 5000.0,
            'reason': 'Demo: second amendment waiting for the manager.'})
        pending.action_submit()
        ctx.reg('lcamd_pending', pending)
        rejected = Amend.create({
            'lc_id': lc.id, 'bank_reference': 'DEMO-SWIFT-0003', 'amount_change': 40000.0,
            'reason': 'Demo: amendment that the manager rejects.'})
        rejected.action_submit()
        ctx.u(rejected, 'lc_manager')._do_reject('Demo: amount is not supported by the contract.')
        ctx.reg('lcamd_rejected', rejected)
        new_shipment(ctx, lc, 'i1', 20000.0, 5, 25, upto='planned', invoice='DEMO-INV-I1')
        add_documents(ctx, lc, ctx.need('shp_i1'), ['commercial_invoice', 'bl_awb'], received=False)

    ctx.step('lc.lc_a', lc_a)
    ctx.step('lc.lc_b', lc_b)
    ctx.step('lc.lc_c', lc_c)
    ctx.step('lc.lc_states', lc_states)
    ctx.step('lc.lc_amendments', lc_amendments)
