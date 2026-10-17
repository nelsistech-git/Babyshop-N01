# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

BOND_LOCATION_FIELDS = {'bond_status', 'bond_license_ref', 'bond_authorized_from', 'bond_authorized_to'}


class StockLocation(models.Model):
    _inherit = 'stock.location'

    bond_status = fields.Selection(
        [('non_bonded', 'Non-Bonded'), ('bonded', 'Bonded')],
        string='Bond Status', default='non_bonded', required=True, index=True, copy=False,
        help='Changed only through an approved Bond Classification Request.')
    bond_license_ref = fields.Char(string='Bond License Reference', copy=False)
    bond_authorized_from = fields.Date(string='Bond Authorized From', copy=False)
    bond_authorized_to = fields.Date(string='Bond Authorized Until', copy=False)
    bond_authorization_valid = fields.Boolean(
        string='Bond Authorization Valid', compute='_compute_bond_authorization_valid')

    def _bond_is_authorized(self, on_date=None):
        """True when the location is a bond-authorized internal location on the given date."""
        self.ensure_one()
        on_date = on_date or fields.Date.context_today(self)
        if self.usage != 'internal' or self.bond_status != 'bonded' or not self.bond_license_ref:
            return False
        if self.bond_authorized_from and self.bond_authorized_from > on_date:
            return False
        if self.bond_authorized_to and self.bond_authorized_to < on_date:
            return False
        return True

    def _compute_bond_authorization_valid(self):
        for location in self:
            location.bond_authorization_valid = (
                location.bond_status == 'bonded' and location._bond_is_authorized())

    @api.constrains('bond_status', 'usage', 'bond_license_ref', 'location_id',
                    'bond_authorized_from', 'bond_authorized_to')
    def _check_bond_configuration(self):
        for location in self:
            if location.bond_status != 'bonded':
                parent = location.location_id
                if parent.bond_status == 'bonded' and location.usage == 'internal':
                    raise ValidationError(_(
                        'Location "%(loc)s" is below the bonded location "%(parent)s" and must be bonded too.',
                        loc=location.display_name, parent=parent.display_name))
                continue
            if location.usage != 'internal':
                raise ValidationError(_('Only internal locations can be bonded ("%s").', location.display_name))
            if not location.bond_license_ref:
                raise ValidationError(_('A bonded location needs a bond license reference ("%s").',
                                        location.display_name))
            if (location.bond_authorized_from and location.bond_authorized_to
                    and location.bond_authorized_from > location.bond_authorized_to):
                raise ValidationError(_('Bond authorization start date is after the end date ("%s").',
                                        location.display_name))

    @api.model_create_multi
    def create(self, vals_list):
        allowed = self.env.context.get('bond_classification_apply')
        for vals in vals_list:
            parent = self.browse(vals.get('location_id'))
            inherited = False
            if (parent.bond_status == 'bonded' and vals.get('usage', 'internal') == 'internal'
                    and 'bond_status' not in vals):
                vals.update({
                    'bond_status': 'bonded',
                    'bond_license_ref': parent.bond_license_ref,
                    'bond_authorized_from': parent.bond_authorized_from,
                    'bond_authorized_to': parent.bond_authorized_to,
                })
                inherited = True
            if vals.get('bond_status') == 'bonded' and not (allowed or inherited):
                raise UserError(_('A location can only become bonded through an approved '
                                  'Bond Classification Request.'))
        return super().create(vals_list)

    def write(self, vals):
        if BOND_LOCATION_FIELDS & set(vals) and not self.env.context.get('bond_classification_apply'):
            raise UserError(_('Bond classification of a location can only be changed through an approved '
                              'Bond Classification Request with supporting evidence.'))
        return super().write(vals)
