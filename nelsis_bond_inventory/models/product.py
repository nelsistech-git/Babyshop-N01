# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    bond_eligible = fields.Boolean(
        string='Bond Eligible', default=False, copy=False, tracking=True,
        help='The product may be received and stored as bonded stock. Imported goods are never '
             'bonded automatically. Changed only through an approved Bond Classification Request.')
    bond_hs_code = fields.Char(string='HS Code (Bond)', help='Default HS code copied to bond receipt lines.')
    bond_requires_expiry = fields.Boolean(
        string='Requires Expiry Date (Bond)',
        help='Chemical or other perishable goods: an expiry date is mandatory on receipt.')

    @api.constrains('bond_eligible', 'tracking')
    def _check_bond_eligible_tracking(self):
        for product in self:
            if product.bond_eligible and product.tracking not in ('lot', 'serial'):
                raise ValidationError(_(
                    'Bond-eligible product "%s" must be tracked by lots or serial numbers so bonded '
                    'quantities stay traceable to the LC / Bill of Entry.', product.display_name))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('bond_classification_apply'):
            for vals in vals_list:
                if vals.get('bond_eligible'):
                    raise UserError(_('Bond eligibility can only be granted through an approved '
                                      'Bond Classification Request.'))
        return super().create(vals_list)

    def write(self, vals):
        if 'bond_eligible' in vals and not self.env.context.get('bond_classification_apply'):
            if any(product.bond_eligible != bool(vals['bond_eligible']) for product in self):
                raise UserError(_('Bond eligibility can only be changed through an approved '
                                  'Bond Classification Request with supporting evidence.'))
        return super().write(vals)
