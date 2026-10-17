# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

from .bond_compliance_common import KEY_RE, WORKFLOW_CTX


class BondComplianceRuleParameter(models.Model):
    _name = 'bond.compliance.rule.parameter'
    _description = 'Bond Compliance Rule Parameter'
    _order = 'rule_id, sequence, id'

    rule_id = fields.Many2one(
        'bond.compliance.rule', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Parameter', required=True)
    key = fields.Char(
        required=True,
        help='Technical key (lower-case, digits, underscore). Calling modules pass the '
             'actual value under this key when evaluating the rule.')
    value_type = fields.Selection(
        [('integer', 'Integer'), ('float', 'Decimal'), ('char', 'Text'),
         ('boolean', 'Yes / No'), ('date', 'Date')],
        required=True, default='integer')
    operator = fields.Selection(
        [('none', 'Reference only'), ('eq', '= equals'), ('ne', '!= not equal'),
         ('lt', '< less than'), ('le', '<= at most'), ('gt', '> greater than'),
         ('ge', '>= at least')],
        required=True, default='none',
        help='How the actual value supplied by a calling module is compared with the '
             'configured value. "Reference only" parameters are returned but not checked.')
    value_integer = fields.Integer()
    value_float = fields.Float(digits=(16, 4))
    value_char = fields.Char()
    value_boolean = fields.Boolean()
    value_date = fields.Date()
    value_is_set = fields.Boolean(
        string='Value Confirmed', default=False,
        help='Tick only after the value has been taken from the official source. '
             'No value is ever pre-filled by this addon.')
    value_display = fields.Char(compute='_compute_value_display')
    unit = fields.Char()
    is_statutory = fields.Boolean(
        string='Statutory', default=True,
        help='Statutory values need a confirmed value and a source note before review.')
    is_required_input = fields.Boolean(
        string='Input Required',
        help='When ticked, evaluation fails if the calling module does not supply this key.')
    source_note = fields.Char(
        string='Source Clause', help='Official clause / paragraph the value is taken from.')

    # ------------------------------------------------------------------
    @api.depends('value_type', 'value_is_set', 'value_integer', 'value_float',
                 'value_char', 'value_boolean', 'value_date', 'unit')
    def _compute_value_display(self):
        for param in self:
            if not param.value_is_set:
                param.value_display = _('(not set)')
                continue
            value = param.get_value()
            if param.value_type == 'boolean':
                text = _('Yes') if value else _('No')
            else:
                text = str(value if value not in (None, False) else '')
            param.value_display = ('%s %s' % (text, param.unit or '')).strip()

    def get_value(self):
        """Return the typed configured value, or None when not confirmed."""
        self.ensure_one()
        if not self.value_is_set:
            return None
        return {
            'integer': self.value_integer,
            'float': self.value_float,
            'char': self.value_char,
            'boolean': self.value_boolean,
            'date': self.value_date,
        }[self.value_type]

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('key')
    def _check_key(self):
        for param in self:
            if not KEY_RE.match(param.key or ''):
                raise ValidationError(_(
                    'Parameter key "%s" is invalid. Use lower-case letters, digits and "_" '
                    'and start with a letter.', param.key))

    @api.constrains('rule_id', 'key')
    def _check_unique_key(self):
        for param in self:
            duplicate = self.search_count([
                ('rule_id', '=', param.rule_id.id), ('key', '=', param.key),
                ('id', '!=', param.id)])
            if duplicate:
                raise ValidationError(_(
                    'Parameter key "%s" is used more than once in the same rule.', param.key))

    @api.constrains('value_type', 'operator')
    def _check_operator(self):
        for param in self:
            if param.value_type in ('char', 'boolean') and param.operator not in ('none', 'eq', 'ne'):
                raise ValidationError(_(
                    'Parameter "%s": text and Yes/No values can only use "equals" or "not equal".',
                    param.name))

    # ------------------------------------------------------------------
    # Lock parameters once the parent rule leaves draft
    # ------------------------------------------------------------------
    def _check_parent_editable(self, rules):
        if self.env.context.get(WORKFLOW_CTX):
            return
        for rule in rules:
            if rule.verification_status != 'draft':
                raise UserError(_(
                    'Parameters of rule %s are locked because the rule is not a draft.',
                    rule.display_name))

    @api.model_create_multi
    def create(self, vals_list):
        rules = self.env['bond.compliance.rule'].browse(
            [vals['rule_id'] for vals in vals_list if vals.get('rule_id')])
        self._check_parent_editable(rules)
        return super().create(vals_list)

    def write(self, vals):
        rules = self.mapped('rule_id')
        if vals.get('rule_id'):
            rules |= self.env['bond.compliance.rule'].browse(vals['rule_id'])
        self._check_parent_editable(rules)
        return super().write(vals)

    def unlink(self):
        self._check_parent_editable(self.mapped('rule_id'))
        return super().unlink()

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def _coerce(self, actual):
        self.ensure_one()
        if self.value_type == 'integer':
            if isinstance(actual, bool):
                raise ValueError('boolean is not an integer')
            number = float(actual)
            if number != int(number):
                raise ValueError('not an integer')
            return int(number)
        if self.value_type == 'float':
            if isinstance(actual, bool):
                raise ValueError('boolean is not a number')
            return float(actual)
        if self.value_type == 'boolean':
            if actual in (True, False):
                return bool(actual)
            raise ValueError('not a boolean')
        if self.value_type == 'date':
            value = fields.Date.to_date(actual)
            if not value:
                raise ValueError('not a date')
            return value
        return str(actual).strip()

    def _compare(self, actual, expected):
        """Return -1, 0 or 1 (for text / boolean only 0 or 1 is meaningful)."""
        self.ensure_one()
        if self.value_type == 'float':
            return float_compare(actual, expected, precision_digits=4)
        if self.value_type == 'char':
            return 0 if actual.lower() == (expected or '').strip().lower() else 1
        if self.value_type == 'boolean':
            return 0 if actual == bool(expected) else 1
        return (actual > expected) - (actual < expected)

    def _evaluate(self, values):
        """Evaluate one parameter against the supplied ``values`` dict."""
        self.ensure_one()
        values = values or {}
        result = {
            'key': self.key, 'name': self.name, 'operator': self.operator,
            'expected': self.get_value(), 'actual': values.get(self.key),
            'unit': self.unit or '', 'result': 'skipped', 'message': '',
        }
        if self.operator == 'none':
            return result
        if not self.value_is_set:
            result.update(result='fail', message=_(
                'Parameter "%s" has no confirmed value.', self.name))
            return result
        actual = result['actual']
        if actual is None or actual == '':
            if self.is_required_input:
                result.update(result='fail', message=_(
                    'Required input "%s" was not supplied.', self.key))
            return result
        try:
            actual = self._coerce(actual)
        except (ValueError, TypeError):
            result.update(result='fail', message=_(
                'Input "%(key)s" has an invalid value: %(value)s', key=self.key, value=actual))
            return result
        cmp_value = self._compare(actual, self.get_value())
        passed = {
            'eq': cmp_value == 0, 'ne': cmp_value != 0, 'lt': cmp_value < 0,
            'le': cmp_value <= 0, 'gt': cmp_value > 0, 'ge': cmp_value >= 0,
        }[self.operator]
        result['actual'] = actual
        if passed:
            result['result'] = 'pass'
        else:
            result.update(result='fail', message=_(
                '%(name)s: actual %(actual)s does not satisfy "%(op)s %(expected)s".',
                name=self.name, actual=actual, op=self.operator, expected=self.get_value()))
        return result
