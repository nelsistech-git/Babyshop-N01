# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockLot(models.Model):
    _inherit = 'stock.lot'

    bond_status = fields.Selection(
        [('non_bonded', 'Non-Bonded'), ('bonded', 'Bonded')],
        string='Bond Status', default='non_bonded', required=True, index=True, copy=False,
        help='Set when the lot is created by a bond receipt; changed only via an approved '
             'Bond Classification Request.')
    bond_receipt_id = fields.Many2one(
        'bond.inventory.receipt', string='Origin Bond Receipt', readonly=True, copy=False,
        index=True, ondelete='restrict')
    bond_consignment_id = fields.Many2one(
        'bond.inventory.consignment', string='Consignment', readonly=True, copy=False,
        index=True, ondelete='restrict')
    bond_lc_label = fields.Char(string='LC (at receipt)', readonly=True, copy=False, index=True)
    bond_boe_number = fields.Char(string='Bill of Entry No. (at receipt)', readonly=True, copy=False, index=True)
    bond_hs_code = fields.Char(string='HS Code (at receipt)', readonly=True, copy=False)
    bond_expiry_date = fields.Date(string='Expiry Date', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('bond_classification_apply'):
            for vals in vals_list:
                if vals.get('bond_status') == 'bonded':
                    raise UserError(_('A lot can only be bonded by a validated bond receipt or an '
                                      'approved Bond Classification Request.'))
        return super().create(vals_list)

    def write(self, vals):
        if 'bond_status' in vals and not self.env.context.get('bond_classification_apply'):
            if any(lot.bond_status != vals['bond_status'] for lot in self):
                raise UserError(_('Bond classification of a lot can only be changed through an approved '
                                  'Bond Classification Request with supporting evidence.'))
        return super().write(vals)
