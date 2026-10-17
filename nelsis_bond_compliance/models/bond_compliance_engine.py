# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
"""Rule evaluation interface for other Nelsis Bond Warehouse modules.

STATUS: DRAFT interface (API_VERSION 1.0-draft). It must be approved before other
modules rely on it. See docs/technical_contract.md.
"""
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .bond_compliance_common import DISCLAIMER, normalize_code


class BondComplianceEngine(models.AbstractModel):
    _name = 'bond.compliance.engine'
    _description = 'Bond Compliance Rule Evaluation Interface'

    API_VERSION = '1.0-draft'

    # ------------------------------------------------------------------
    @api.model
    def _to_date(self, value):
        if not value:
            return fields.Date.context_today(self)
        result = fields.Date.to_date(value)
        if not result:
            raise UserError(_('Invalid evaluation date: %s', value))
        return result

    @api.model
    def _resolve_license_category(self, category):
        Category = self.env['bond.compliance.license.category'].sudo()
        if not category:
            return Category
        if isinstance(category, models.BaseModel):
            if category._name != Category._name:
                raise UserError(_('Invalid license category record.'))
            return category.sudo()[:1]
        if isinstance(category, int):
            record = Category.browse(category).exists()
        else:
            record = Category.search([('code', '=', normalize_code(str(category)))], limit=1)
        if not record:
            raise UserError(_('Unknown license category: %s', category))
        return record

    # ------------------------------------------------------------------
    # Rule lookup
    # ------------------------------------------------------------------
    @api.model
    def get_applicable_rules(self, code, on_date=None, license_category=None):
        """Return all rule versions matching code, date and category.

        Only rules that went through review, approval and activation are considered
        (status active or superseded). Superseded versions stay selectable for the
        dates they were in force, so historical dates keep returning the old version.
        """
        on_date = self._to_date(on_date)
        category = self._resolve_license_category(license_category)
        domain = [
            ('code', '=', normalize_code(code)),
            ('verification_status', 'in', ('active', 'superseded')),
            ('effective_from', '<=', on_date),
            '|', ('effective_to', '=', False), ('effective_to', '>=', on_date),
        ]
        if category:
            domain.append(('applicable_category_ids', 'in', category.ids))
        return self.env['bond.compliance.rule'].sudo().search(
            domain, order='effective_from desc, version desc')

    @api.model
    def get_applicable_rule(self, code, on_date=None, license_category=None):
        """Return the single applicable rule version or an empty recordset."""
        rules = self.get_applicable_rules(code, on_date, license_category)
        if len(rules) > 1:
            raise ValidationError(_(
                'More than one rule version applies to code %(code)s. Pass a license '
                'category to disambiguate.', code=code))
        return rules

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    @api.model
    def evaluate(self, code, on_date=None, license_category=None, values=None,
                 documents=None, res_model=None, res_id=None, reference=None, log=True):
        """Evaluate a rule and return a plain, JSON-friendly dict.

        :param code: rule code (all versions share it)
        :param on_date: transaction date used to pick the rule version (default today)
        :param license_category: category code, id or record
        :param values: dict {parameter key: actual value}
        :param documents: iterable of document type codes (or records) that are available
        :param res_model, res_id, reference: link to the calling business document
        :param log: store an immutable evaluation log entry
        :return: dict with keys status (passed / failed / no_rule / ambiguous), passed,
            rule_id, rule_version, parameter_results, missing_document_types, messages,
            exception_ids, covered_by_exception, evaluation_id, disclaimer
        """
        values = values or {}
        on_date = self._to_date(on_date)
        category = self._resolve_license_category(license_category)
        code = normalize_code(code)
        result = {
            'api_version': self.API_VERSION,
            'rule_code': code,
            'on_date': on_date,
            'license_category': category.code or None,
            'status': 'no_rule',
            'passed': False,
            'rule_id': False,
            'rule_version': False,
            'official_reference': False,
            'source_url': False,
            'requires_professional_verification': False,
            'parameter_results': [],
            'missing_document_types': [],
            'messages': [],
            'exception_ids': [],
            'covered_by_exception': False,
            'evaluation_id': False,
            'disclaimer': DISCLAIMER,
        }
        rules = self.get_applicable_rules(code, on_date, category)
        rule = self.env['bond.compliance.rule']
        if not rules:
            result['messages'].append(_(
                'No activated rule %(code)s applies on %(date)s for the given category.',
                code=code, date=on_date))
        elif len(rules) > 1:
            result['status'] = 'ambiguous'
            result['messages'].append(_(
                'More than one rule version applies; pass a license category.'))
        else:
            rule = rules
            self._evaluate_rule(rule, result, values, documents)
            self._attach_exceptions(rule, result, on_date, res_model, res_id, reference)
        if log:
            result['evaluation_id'] = self._log(
                rule, result, on_date, res_model, res_id, reference)
        return result

    @api.model
    def _evaluate_rule(self, rule, result, values, documents):
        provided = set()
        for doc in documents or []:
            code = doc.code if isinstance(doc, models.BaseModel) else str(doc)
            provided.add(normalize_code(code))
        missing = rule.required_document_type_ids.filtered(lambda t: t.code not in provided)
        parameter_results = [p._evaluate(values) for p in rule.parameter_ids.sorted('sequence')]
        failures = [p for p in parameter_results if p['result'] == 'fail']
        result.update(
            rule_id=rule.id,
            rule_version=rule.version,
            official_reference=rule.official_reference,
            source_url=rule.source_url,
            requires_professional_verification=rule.requires_professional_verification,
            parameter_results=parameter_results,
            missing_document_types=missing.mapped('code'),
        )
        result['messages'].extend(p['message'] for p in failures if p['message'])
        for doc_type in missing:
            result['messages'].append(_('Required document missing: %s', doc_type.name))
        if failures or missing:
            result['status'] = 'failed'
        else:
            result['status'] = 'passed'
            result['passed'] = True

    @api.model
    def _attach_exceptions(self, rule, result, on_date, res_model, res_id, reference):
        domain = [
            ('rule_id', '=', rule.id), ('state', '=', 'approved'),
            ('valid_from', '<=', on_date), ('valid_to', '>=', on_date),
        ]
        if res_model and res_id:
            domain += [('res_model', '=', res_model), ('res_id', '=', res_id)]
        elif reference:
            domain.append(('reference', '=', reference))
        else:
            return
        exceptions = self.env['bond.compliance.exception'].sudo().search(domain)
        result['exception_ids'] = exceptions.ids
        # An exception never turns a failed result into a pass; callers decide.
        result['covered_by_exception'] = bool(exceptions) and result['status'] == 'failed'

    @api.model
    def _log(self, rule, result, on_date, res_model, res_id, reference):
        ref = reference or ('%s,%s' % (res_model, res_id) if res_model and res_id else False)
        entry = self.env['bond.compliance.evaluation'].sudo().create({
            'name': '%s%s / %s' % (
                result['rule_code'],
                (' v%s' % rule.version) if rule else '',
                ref or on_date),
            'rule_id': rule.id or False,
            'rule_code': result['rule_code'],
            'rule_version': rule.version if rule else 0,
            'official_reference': rule.official_reference if rule else False,
            'res_model': res_model or False,
            'res_id': res_id or 0,
            'reference': ref,
            'evaluated_on': on_date,
            'status': result['status'],
            'passed': result['passed'],
            'covered_by_exception': result['covered_by_exception'],
            'result_json': json.dumps(result, default=str, sort_keys=True),
        })
        return entry.id
