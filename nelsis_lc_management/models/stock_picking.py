# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError

from .constants import G_BOND, G_OFFICER, LC_VIEW_GROUPS, LIVE_STATES


class StockPicking(models.Model):
    """Adds LC traceability links to standard receipts.

    This is a link only: no stock move, move line or quant is created,
    changed or validated by this module.
    """
    _inherit = 'stock.picking'

    lc_id = fields.Many2one('nelsis.lc', string='Letter of Credit', index=True, copy=False,
                            tracking=True, ondelete='restrict', groups=LC_VIEW_GROUPS)
    lc_shipment_id = fields.Many2one('nelsis.lc.shipment', string='LC Shipment', index=True, copy=False,
                                     tracking=True, ondelete='restrict', groups=LC_VIEW_GROUPS,
                                     domain="[('lc_id', '=', lc_id)]")

    @api.constrains('lc_id', 'lc_shipment_id', 'picking_type_id', 'company_id')
    def _check_nelsis_lc_link(self):
        for picking in self.sudo():
            if not picking.lc_id:
                if picking.lc_shipment_id:
                    raise ValidationError(_('Select the Letter of Credit before choosing an LC shipment.'))
                continue
            if picking.picking_type_code != 'incoming':
                raise ValidationError(_('Only receipts can be linked to a Letter of Credit.'))
            if picking.lc_id.company_id != picking.company_id:
                raise ValidationError(_('The Letter of Credit belongs to a different company.'))
            if picking.lc_id.state not in LIVE_STATES:
                raise ValidationError(_('LC %s is not open for receipts (status: %s).',
                                        picking.lc_id.name,
                                        dict(picking.lc_id._fields['state'].selection)[picking.lc_id.state]))
            if picking.lc_shipment_id and picking.lc_shipment_id.lc_id != picking.lc_id:
                raise ValidationError(_('The LC shipment does not belong to the selected LC.'))

    @api.onchange('lc_shipment_id')
    def _onchange_lc_shipment_id(self):
        if self.lc_shipment_id:
            self.lc_id = self.lc_shipment_id.lc_id

    @api.onchange('lc_id')
    def _onchange_lc_id(self):
        if self.lc_shipment_id and self.lc_shipment_id.lc_id != self.lc_id:
            self.lc_shipment_id = False

    def _check_lc_link_rights(self, vals):
        if self.env.su or not ({'lc_id', 'lc_shipment_id'} & set(vals)):
            return
        user = self.env.user
        if not (user.has_group(G_OFFICER) or user.has_group(G_BOND)):
            raise AccessError(_('Only LC Officers or Bond Warehouse Officers may link receipts to a Letter of Credit.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_lc_link_rights(vals)
        records = super().create(vals_list)
        for picking in records.sudo().filtered('lc_id'):
            picking.lc_id._log(_('Receipt %s linked', picking.name))
        return records

    def write(self, vals):
        self._check_lc_link_rights(vals)
        before = {}
        if 'lc_id' in vals:
            before = {p.id: p.lc_id for p in self.sudo()}
            if any(p.lc_id.id != vals['lc_id'] for p in self.sudo()) and 'lc_shipment_id' not in vals:
                vals = dict(vals, lc_shipment_id=False)
        res = super().write(vals)
        for picking in self.sudo():
            old = before.get(picking.id)
            if 'lc_id' in vals and old != picking.lc_id:
                if old:
                    old._log(_('Receipt %s unlinked', picking.name))
                if picking.lc_id:
                    picking.lc_id._log(_('Receipt %s linked', picking.name))
        return res
