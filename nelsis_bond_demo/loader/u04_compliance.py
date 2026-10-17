# -*- coding: utf-8 -*-
"""Compliance rule register: rules through submit -> review -> approve -> activate with three
different users, a new version, exceptions and evaluation log entries.
Every value is invented ("DEMO"); parameters are flagged non-statutory."""
from odoo import Command

from .consts import RULE_APPLICABILITY, RULE_REF, RULE_URL

NS = 'nelsis_bond_compliance.'


def _categories(ctx):
    env = ctx.env
    return [env.ref(NS + 'bond_license_category_leather').id,
            env.ref(NS + 'bond_license_category_footwear').id]


def _doc_types(ctx, *names):
    return [ctx.env.ref(NS + 'bond_doc_type_' + n).id for n in names]


def _param(key, name, vtype, operator, value, unit):
    vals = {
        'name': name, 'key': key, 'value_type': vtype, 'operator': operator,
        'value_is_set': True, 'is_statutory': False, 'unit': unit,
        'source_note': 'DEMO value (fictitious) - not taken from any official source',
    }
    vals['value_' + vtype if vtype != 'float' else 'value_float'] = value
    return Command.create(vals)


RULES = [
    # key, code, title, category xmlid suffix, parameters, document types, prof. verification
    ('storage', 'DEMO_STORAGE_PERIOD', 'Demo - maximum storage period (fictitious value)',
     'storage_period', [_param('max_storage_days', 'Maximum storage days', 'integer', 'le', 365, 'days')],
     [], False),
    ('docs', 'DEMO_RECEIPT_DOCS', 'Demo - documents required with a bonded receipt',
     'documentation', [], ['lc_copy', 'bill_of_entry', 'commercial_invoice'], True),
    ('entitlement', 'DEMO_ENTITLEMENT_LIMIT', 'Demo - entitlement utilization ceiling',
     'entitlement', [_param('utilization_limit_pct', 'Utilization ceiling', 'float', 'le', 100.0, '%')],
     [], False),
    ('lcvalidity', 'DEMO_LC_VALIDITY', 'Demo - LC validity check (still a draft)',
     'documentation', [], ['lc_copy'], False),
    ('verify', 'DEMO_RECEIPT_VERIFICATION', 'Demo - receipt verification (under review)',
     'receipt_verification', [], ['bill_of_entry'], False),
    ('register', 'DEMO_STOCK_REGISTER', 'Demo - stock register keeping (rejected once)',
     'stock_register', [], [], False),
    ('licvalid', 'DEMO_BOND_LICENSE_VALIDITY', 'Demo - license validity (reviewed, waiting for approval)',
     'bond_license', [], ['lc_copy'], False),
]

# How far each rule goes: 'active', 'reviewed', 'under_review', 'rejected', 'draft'
TARGET = {'storage': 'active', 'docs': 'active', 'entitlement': 'active', 'lcvalidity': 'draft',
          'verify': 'under_review', 'register': 'rejected', 'licvalid': 'reviewed'}


def run(ctx):
    env = ctx.env

    def make_rule(spec):
        key, code, title, categ, params, doc_types, prof = spec

        def _do():
            Rule = ctx.model_as('compliance_officer', 'bond.compliance.rule')
            vals = {
                'name': title, 'code': code,
                'rule_category_id': env.ref(NS + 'bond_rule_category_' + categ).id,
                'official_reference': RULE_REF, 'source_url': RULE_URL,
                'publication_date': ctx.d(-400), 'effective_from': ctx.d(-365),
                'applicability': RULE_APPLICABILITY,
                'description': 'Demo rule with invented content. Replace with the verified official text.',
                'applicable_category_ids': [Command.set(_categories(ctx))],
                'parameter_ids': params,
                'required_document_type_ids': [Command.set(_doc_types(ctx, *doc_types))],
                'next_review_date': ctx.d(90),
            }
            if prof:
                vals.update({
                    'requires_professional_verification': True,
                    'professional_verification_note': 'Demo: interpretation to be confirmed by a professional.',
                    'professional_verified_by': 'Demo Customs Consultant (fictitious)',
                    'professional_verified_date': ctx.d(-380),
                })
            rule = Rule.create(vals)
            ctx.reg('rule_' + key, rule)
            target = TARGET[key]
            if target == 'draft':
                return
            rule.action_submit_review()
            if target == 'under_review':
                return
            if target == 'rejected':
                ctx.u(rule, 'compliance_reviewer').action_reject(
                    'Demo: source URL does not point to an official publication. Please correct and resubmit.')
                return
            ctx.u(rule, 'compliance_reviewer').action_mark_reviewed()
            if target == 'reviewed':
                return
            approver = ctx.u(rule, 'compliance_approver')
            approver.action_approve()
            approver.action_activate()
        return _do

    def new_version():
        v1 = ctx.need('rule_storage')
        officer_v1 = ctx.u(v1, 'compliance_officer')
        officer_v1.action_new_version()
        v2 = env['bond.compliance.rule'].with_context(active_test=False).search(
            [('code', '=', v1.code), ('version', '=', 2)], limit=1)
        ctx.reg('rule_storage_v2', v2)
        officer_v2 = ctx.u(v2, 'compliance_officer')
        officer_v2.write({
            'official_reference': 'DEMO/SRO-0001A (fictitious amendment)',
            'source_url': RULE_URL + '/amended',
            'publication_date': ctx.d(-45), 'effective_from': ctx.d(-30),
            'next_review_date': ctx.d(150),
        })
        officer_v2.parameter_ids.write({'value_integer': 540})
        officer_v2.action_submit_review()
        ctx.u(v2, 'compliance_reviewer').action_mark_reviewed()
        approver = ctx.u(v2, 'compliance_approver')
        approver.action_approve()
        approver.action_activate()

    def exceptions():
        rule = ctx.need('rule_entitlement')
        Exc = ctx.model_as('compliance_officer', 'bond.compliance.exception')
        base = {'rule_id': rule.id, 'valid_from': ctx.d(-10), 'valid_to': ctx.d(60)}
        approved = Exc.create(dict(base, reference='DEMO-EXC-0001',
                                   reason='Demo: temporary ceiling relief during year-end stock take.',
                                   conditions='Fictitious conditions: weekly review by the manager.'))
        approved.action_submit()
        ctx.u(approved, 'compliance_approver').action_approve()
        ctx.reg('exc_approved', approved)
        submitted = Exc.create(dict(base, reference='DEMO-EXC-0002',
                                    reason='Demo: submitted exception waiting for the approver.'))
        submitted.action_submit()
        ctx.reg('exc_submitted', submitted)
        draft = Exc.create(dict(base, reference='DEMO-EXC-0003',
                                reason='Demo: draft exception, not submitted.'))
        ctx.reg('exc_draft', draft)
        rejected = Exc.create(dict(base, reference='DEMO-EXC-0004',
                                   reason='Demo: exception that the approver rejects.'))
        rejected.action_submit()
        ctx.u(rejected, 'compliance_approver').action_reject('Demo: justification is too vague.')
        ctx.reg('exc_rejected', rejected)

    def evaluations():
        engine = env['bond.compliance.engine']
        category = 'LEATHER_FACTORY'
        engine.evaluate('DEMO_STORAGE_PERIOD', license_category=category,
                        values={'max_storage_days': 120}, reference='DEMO storage check - within limit')
        engine.evaluate('DEMO_STORAGE_PERIOD', license_category=category,
                        values={'max_storage_days': 700}, reference='DEMO storage check - over limit')
        engine.evaluate('DEMO_STORAGE_PERIOD', on_date=ctx.d(-100), license_category=category,
                        values={'max_storage_days': 380},
                        reference='DEMO historical check - earlier rule version applies')
        engine.evaluate('DEMO_RECEIPT_DOCS', license_category=category,
                        documents=['LC_COPY', 'BILL_OF_ENTRY', 'COMMERCIAL_INVOICE'],
                        reference='DEMO document check - complete set')
        engine.evaluate('DEMO_RECEIPT_DOCS', license_category=category,
                        documents=['LC_COPY'], reference='DEMO document check - documents missing')
        engine.evaluate('DEMO_ENTITLEMENT_LIMIT', license_category=category,
                        values={'utilization_limit_pct': 85.0}, reference='DEMO entitlement ceiling check')
        engine.evaluate('DEMO_UNKNOWN_RULE', license_category=category,
                        reference='DEMO check - no rule defined')

    for spec in RULES:
        ctx.step('compliance.rule_' + spec[0], make_rule(spec))
    ctx.step('compliance.rule_storage_v2', new_version)
    ctx.step('compliance.exceptions', exceptions)
    ctx.step('compliance.evaluations', evaluations)
