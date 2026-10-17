# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .bond_compliance_common import CODE_RE, normalize_code


class BondComplianceRuleCategory(models.Model):
    _name = 'bond.compliance.rule.category'
    _description = 'Bond Compliance Rule Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    active = fields.Boolean(default=True)
    rule_count = fields.Integer(compute='_compute_rule_count')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The category code must be unique.'),
    ]

    def _compute_rule_count(self):
        Rule = self.env['bond.compliance.rule'].with_context(active_test=False)
        for rec in self:
            rec.rule_count = Rule.search_count([('rule_category_id', '=', rec.id)])

    @api.constrains('code')
    def _check_code(self):
        for rec in self:
            if not CODE_RE.match(rec.code or ''):
                raise ValidationError(_(
                    'Code "%s" is invalid. Use upper-case letters, digits, "_", "-" or ".".', rec.code))

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(v, code=normalize_code(v.get('code'))) for v in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('code'):
            vals = dict(vals, code=normalize_code(vals['code']))
        return super().write(vals)


class BondComplianceLicenseCategory(models.Model):
    _name = 'bond.compliance.license.category'
    _description = 'Bond License / Factory Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text(
        help='Map this grouping to the official license category in the NBR / Customs '
             'register during rule review. Never assume garment rules apply to leather '
             'or footwear factories.')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The license category code must be unique.'),
    ]

    @api.constrains('code')
    def _check_code(self):
        for rec in self:
            if not CODE_RE.match(rec.code or ''):
                raise ValidationError(_(
                    'Code "%s" is invalid. Use upper-case letters, digits, "_", "-" or ".".', rec.code))

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(v, code=normalize_code(v.get('code'))) for v in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('code'):
            vals = dict(vals, code=normalize_code(vals['code']))
        return super().write(vals)

    def unlink(self):
        used = self.env['bond.compliance.rule'].with_context(active_test=False).search_count(
            [('applicable_category_ids', 'in', self.ids)])
        if used:
            raise UserError(_(
                'This license category is used by compliance rules and cannot be deleted. '
                'Archive it instead.'))
        return super().unlink()


class BondComplianceDocumentType(models.Model):
    _name = 'bond.compliance.document.type'
    _description = 'Bond Compliance Document Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The document type code must be unique.'),
    ]

    @api.constrains('code')
    def _check_code(self):
        for rec in self:
            if not CODE_RE.match(rec.code or ''):
                raise ValidationError(_(
                    'Code "%s" is invalid. Use upper-case letters, digits, "_", "-" or ".".', rec.code))

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(v, code=normalize_code(v.get('code'))) for v in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('code'):
            vals = dict(vals, code=normalize_code(vals['code']))
        return super().write(vals)

    def unlink(self):
        used = self.env['bond.compliance.rule'].with_context(active_test=False).search_count(
            [('required_document_type_ids', 'in', self.ids)])
        if used:
            raise UserError(_(
                'This document type is required by compliance rules and cannot be deleted. '
                'Archive it instead.'))
        return super().unlink()
