# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    bond_lc_model_name = fields.Char(
        string='LC Model (technical name)',
        help='Technical model name of the existing LC Management record, discovered from its '
             'source files. Leave empty until verified. Never guessed by this addon.')
    bond_variance_tolerance_pct = fields.Float(
        string='Receipt Variance Tolerance (%)', digits=(5, 2), default=0.0,
        help='Configurable internal threshold: shortage or excess above this percentage of the declared '
             'quantity needs approval. It is NOT a legal limit. Default 0 = any variance needs approval.')
    bond_always_require_approval = fields.Boolean(
        string='Always Require Receipt Approval', default=False)

    @api.constrains('bond_lc_model_name')
    def _check_bond_lc_model_name(self):
        for company in self:
            name = company.bond_lc_model_name
            if name and name not in self.env:
                raise ValidationError(_('Model "%s" does not exist in this database.', name))

    @api.constrains('bond_variance_tolerance_pct')
    def _check_bond_variance_tolerance(self):
        for company in self:
            if not 0.0 <= company.bond_variance_tolerance_pct <= 100.0:
                raise ValidationError(_('The variance tolerance must be between 0 and 100.'))
