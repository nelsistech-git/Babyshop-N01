# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import fields, models, _
from odoo.exceptions import UserError


class NelsisLcLinkReceiptWizard(models.TransientModel):
    """Links existing standard receipts to an LC.  No stock is created or moved."""
    _name = 'nelsis.lc.link.receipt.wizard'
    _description = 'Link Warehouse Receipts to LC'

    lc_id = fields.Many2one('nelsis.lc', string='Letter of Credit', required=True, readonly=True)
    company_id = fields.Many2one(related='lc_id.company_id')
    shipment_id = fields.Many2one('nelsis.lc.shipment', string='LC Shipment',
                                  domain="[('lc_id', '=', lc_id), ('state', '!=', 'cancelled')]")
    picking_ids = fields.Many2many(
        'stock.picking', 'nelsis_lc_link_receipt_picking_rel', 'wizard_id', 'picking_id',
        string='Receipts',
        domain="[('picking_type_code', '=', 'incoming'), ('lc_id', '=', False), "
               "('state', '!=', 'cancel'), ('company_id', '=', company_id)]")

    def action_link(self):
        self.ensure_one()
        if not self.picking_ids:
            raise UserError(_('Select at least one receipt.'))
        vals = {'lc_id': self.lc_id.id}
        if self.shipment_id:
            vals['lc_shipment_id'] = self.shipment_id.id
        # Normal write: group check and constraints of stock.picking apply.
        self.picking_ids.write(vals)
        return {'type': 'ir.actions.act_window_close'}
