# -*- coding: utf-8 -*-
"""Commercial files: compliance matrix, documents (officer submits, manager verifies),
Bills of Entry, quantity discrepancies and every file status."""
from odoo import Command

from .consts import BOE_A, BOE_B, BOE_C, LC_A, LC_B, LC_C
from .ctx import create_optional

NS = 'nelsis_commercial.'
CORE_TYPES = ['ci', 'pl', 'bl', 'boe']

MATRIX = [
    ('Demo: commercial invoice required', 'ci', 'required'),
    ('Demo: packing list required', 'pl', 'required'),
    ('Demo: bill of lading required', 'bl', 'required'),
    ('Demo: bill of entry copy required', 'boe', 'required'),
    ('Demo: certificate of origin (conditional)', 'coo', 'conditional'),
    ('Demo: insurance document (optional)', 'ins', 'optional'),
]


def _type(ctx, code):
    return ctx.env.ref(NS + 'doc_type_' + code)


def new_file(ctx, key, supplier_key, lc_key=None, ttype='import_lc', note='Fictitious demo file.'):
    File = ctx.model_as('lc_officer', 'nelsis.commercial.file')
    vals = {'transaction_type': ttype, 'partner_id': ctx.need('partner_' + supplier_key).id,
            'notes': '<p>%s</p>' % note}
    optional = {}
    lc = ctx.get('lc_' + lc_key) if lc_key else None
    if lc:
        optional['lc_ref'] = 'nelsis.lc,%d' % lc.id
    f = create_optional(File, vals, optional)
    ctx.reg('cf_' + key, f)
    return f


def add_doc(ctx, f, code, number, upto='verified', issue=-40, expiry=None, reason=None):
    """Create a document as the officer and take it to ``upto`` (draft/submitted/verified/rejected)."""
    Doc = ctx.model_as('lc_officer', 'nelsis.commercial.document')
    doc = Doc.create({
        'file_id': f.id, 'document_type_id': _type(ctx, code).id, 'number': number,
        'issue_date': ctx.d(issue), 'expiry_date': ctx.d(expiry) if expiry is not None else False,
        'issuing_org': 'Demo Issuer (fictitious)', 'remarks': 'Fictitious demo document.'})
    att = ctx.attach(doc, 'doc-%s' % number.lower(), '%s (demo)' % _type(ctx, code).name,
                     ['Number: %s' % number, 'File: %s' % f.name])
    doc.write({'attachment_ids': [Command.set([att.id])]})
    if upto == 'draft':
        return doc
    doc.action_submit()
    manager = ctx.u(doc, 'lc_manager')
    if upto == 'verified':
        manager.action_verify()
    elif upto == 'rejected':
        manager.write({'rejection_reason': reason or 'Demo: copy is not legible.'})
        manager.action_reject()
    return doc


def add_boe(ctx, f, number, upto='cleared', date_days=-18):
    Boe = ctx.model_as('lc_officer', 'nelsis.commercial.boe')
    boe = Boe.create({'name': number, 'file_id': f.id, 'date': ctx.d(date_days),
                      'customs_station': 'Demo Customs Station (fictitious)',
                      'invoice_ref': 'DEMO-INV-%s' % number[-4:],
                      'notes': 'Fictitious demo Bill of Entry.'})
    att = ctx.attach(boe, 'boe-%s' % number.lower(), 'Bill of Entry copy (demo)', ['BoE: %s' % number])
    boe.write({'attachment_ids': [Command.set([att.id])]})
    boe.action_submit()
    manager = ctx.u(boe, 'lc_manager')
    if upto in ('verified', 'cleared'):
        manager.action_verify()
    if upto == 'cleared':
        manager.action_clear()
    return boe


def add_lines(ctx, f, specs):
    Line = ctx.model_as('lc_officer', 'nelsis.commercial.line')
    for product_key, qty, value in specs:
        product = ctx.need('pv_' + product_key)
        Line.create({'file_id': f.id, 'source_kind': 'invoice', 'product_id': product.id,
                     'uom_id': product.uom_id.id, 'qty': qty, 'value': value})


def finish_file(ctx, f, picking_keys):
    """Verification -> documents complete -> customs -> cleared -> receipt linked -> done."""
    officer = ctx.u(f, 'lc_officer')
    manager = ctx.u(f, 'lc_manager')
    officer.action_submit()
    officer.action_start_verification()
    return officer, manager


def run(ctx):
    def matrix():
        Rule = ctx.model_as('lc_manager', 'nelsis.commercial.rule')
        for name, code, requirement in MATRIX:
            rule = Rule.create({
                'name': name, 'transaction_type': 'import_lc', 'document_type_id': _type(ctx, code).id,
                'requirement': requirement, 'amendment_status': 'unverified',
                'source_reference': 'DEMO ONLY - configure from the official rule yourself',
                'applicability': 'Fictitious demo rule. Not a statement of any legal requirement.',
                'effective_date': ctx.d(-365), 'department': 'Import & Bond (demo)'})
            ctx.reg('crule_' + code, rule)

    def completed(key, supplier, lc_key, lc_number, boe_no, picking_keys, lines, tag):
        def _run():
            f = new_file(ctx, key, supplier, lc_key, note='Completed import file (%s).' % tag)
            officer, manager = finish_file(ctx, f, picking_keys)
            add_doc(ctx, f, 'ci', 'DEMO-CI-%s' % tag)
            add_doc(ctx, f, 'pl', 'DEMO-PL-%s' % tag)
            add_doc(ctx, f, 'bl', 'DEMO-BL-%s' % tag)
            add_doc(ctx, f, 'boe', 'DEMO-BOEDOC-%s' % tag)
            add_doc(ctx, f, 'coo', 'DEMO-COO-%s' % tag, expiry=300)
            manager.action_docs_complete()
            add_boe(ctx, f, boe_no)
            officer.action_start_customs()
            manager.action_cleared()
            pickings = ctx.env['stock.picking']
            for rk in picking_keys:
                pickings |= ctx.need('receipt_' + rk).picking_id
            f.sudo().write({'picking_ids': [Command.set(pickings.ids)]})
            add_lines(ctx, f, lines)
            officer.action_compute_discrepancies()
            for disc in f.sudo().discrepancy_ids.filtered(lambda d: d.state in ('mismatch', 'uom_review')):
                dm = ctx.u(disc, 'lc_manager')
                dm.write({'explanation': 'Demo: difference explained by the supplier short shipment note.'})
                dm.action_approve()
            manager.action_done()
        return _run

    def shipments():
        Ship = ctx.model_as('lc_officer', 'nelsis.commercial.shipment')
        f = ctx.need('cf_a')
        s = Ship.create({'file_id': f.id, 'transport_mode': 'sea', 'port_loading': 'Demo Port of Loading',
                         'destination': 'Demo Bonded Warehouse', 'vessel': 'MV Demo Voyager',
                         'transport_doc_no': 'DEMO-BL-A1', 'shipment_date': ctx.d(-90),
                         'eta_date': ctx.d(-75)})
        s.action_in_transit()
        s.action_arrived()
        ctx.reg('cship_a', s)
        planned = Ship.create({'file_id': ctx.need('cf_b').id, 'transport_mode': 'air',
                               'transport_doc_no': 'DEMO-AWB-B9', 'shipment_date': ctx.d(4),
                               'eta_date': ctx.d(8), 'is_partial': True, 'partial_no': 2})
        ctx.reg('cship_b2', planned)

    def customs_file():
        f = new_file(ctx, 'c', 'sup_trim', 'c', note='File in customs clearance.')
        officer, manager = finish_file(ctx, f, [])
        for code in CORE_TYPES:
            add_doc(ctx, f, code, 'DEMO-%s-C' % code.upper())
        manager.action_docs_complete()
        add_boe(ctx, f, BOE_C, upto='verified')
        officer.action_start_customs()

    def verification_file():
        f = new_file(ctx, 'v', 'sup_leather', None, note='File under verification with missing documents.')
        officer, _manager = finish_file(ctx, f, [])
        add_doc(ctx, f, 'ci', 'DEMO-CI-V')
        add_doc(ctx, f, 'pl', 'DEMO-PL-V', upto='submitted')
        add_doc(ctx, f, 'coo', 'DEMO-COO-V-EXPIRED', upto='submitted', issue=-400, expiry=-20)
        add_doc(ctx, f, 'bl', 'DEMO-BL-V', upto='rejected', reason='Demo: B/L number does not match the invoice.')
        add_doc(ctx, f, 'ins', 'DEMO-INS-V', upto='draft')

    def other_states():
        returned = new_file(ctx, 'returned', 'sup_chem', None, note='Returned for correction.')
        officer = ctx.u(returned, 'lc_officer')
        officer.action_submit()
        officer.action_start_verification()
        ctx.u(returned, 'lc_manager').action_return()
        hold = new_file(ctx, 'hold', 'sup_leather', None, note='Put on hold by the officer.')
        ctx.u(hold, 'lc_officer').action_submit()
        ctx.u(hold, 'lc_officer').action_hold()
        rejected = new_file(ctx, 'rejected', 'sup_chem', None, note='Rejected by the manager.')
        ctx.u(rejected, 'lc_officer').action_submit()
        ctx.u(rejected, 'lc_manager').action_reject()
        cancelled = new_file(ctx, 'cancelled', 'sup_leather', None, note='Cancelled before submission.')
        ctx.u(cancelled, 'lc_officer').action_cancel()
        new_file(ctx, 'draft', 'sup_trim', None, ttype='local_ref', note='Draft local reference file.')

    ctx.step('commercial.matrix', matrix)
    ctx.step('commercial.file_a', completed('a', 'sup_leather', 'a', LC_A, BOE_A, ['a1', 'a2'],
                                            [('lth_black', 1000.0, 70000.0), ('lth_tan', 600.0, 45000.0)], 'A'))
    ctx.step('commercial.file_b', completed('b', 'sup_chem', 'b', LC_B, BOE_B, ['b1'],
                                            [('chem_pu', 1700.0, 30000.0)], 'B'))
    ctx.step('commercial.shipments', shipments)
    ctx.step('commercial.file_customs', customs_file)
    ctx.step('commercial.file_verification', verification_file)
    ctx.step('commercial.other_states', other_states)
