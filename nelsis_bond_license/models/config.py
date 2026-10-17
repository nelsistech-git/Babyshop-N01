# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BondLicenseType(models.Model):
    _name = 'bond.license.type'
    _description = 'Bond License Type'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char()
    description = fields.Text()
    active = fields.Boolean(default=True)

    _sql_constraints = [('name_uniq', 'unique(name)', 'License type name must be unique.')]


class BondFactoryCategory(models.Model):
    _name = 'bond.factory.category'
    _description = 'Bond Factory Category'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char()
    description = fields.Text()
    active = fields.Boolean(default=True)

    _sql_constraints = [('name_uniq', 'unique(name)', 'Factory category name must be unique.')]


class ResCompany(models.Model):
    _inherit = 'res.company'

    bond_reminder_days = fields.Char(
        string='Bond Reminder Days', default='60,30,15,7',
        help='Comma separated days before expiry at which reminders are scheduled.')
    bond_require_verified_rule = fields.Boolean(
        string='Require Verified Regulatory Basis', default=True,
        help='If set, licenses and entitlements can only be activated after their rule basis is verified.')

    @api.constrains('bond_reminder_days')
    def _check_bond_reminder_days(self):
        for company in self:
            for part in (company.bond_reminder_days or '').split(','):
                part = part.strip()
                if part and not (part.isdigit() and int(part) > 0):
                    raise ValidationError(_('Reminder days must be a comma separated list of positive integers.'))

    def _bond_reminder_thresholds(self):
        self.ensure_one()
        values = set()
        for part in (self.bond_reminder_days or '').split(','):
            part = part.strip()
            if part.isdigit() and int(part) > 0:
                values.add(int(part))
        return sorted(values)
