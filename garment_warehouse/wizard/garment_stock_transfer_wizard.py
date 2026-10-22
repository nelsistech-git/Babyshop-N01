# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Stock Transfer Management (SRS "Stock Transfer Management" / "Internal
Stock Transfer" — Source Location, Destination Location, Material,
Quantity, Responsible Person). Creates the source transfer_out and
destination transfer_in garment.stock.move records together, sharing one
reference, so a transfer can never be recorded as a lopsided single move.
Both legs are created in 'draft' and need Warehouse Manager approval
(garment.stock.move.action_approve_movement) before they affect on-hand
quantity, matching the SRS "Transfer Request -> Approval -> ... -> Location
Update" workflow.
"""
from odoo import fields, models, _
from odoo.exceptions import UserError


class GarmentStockTransferWizard(models.TransientModel):
    _name = 'garment.stock.transfer.wizard'
    _description = 'Garment Stock Transfer Wizard'

    material_id = fields.Many2one('garment.material', string='Material', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    source_warehouse_id = fields.Many2one('garment.warehouse', string='From Warehouse', required=True)
    source_location_id = fields.Many2one('garment.location', string='From Location',
                                          domain="[('warehouse_id', '=', source_warehouse_id)]")
    destination_warehouse_id = fields.Many2one('garment.warehouse', string='To Warehouse', required=True)
    destination_location_id = fields.Many2one('garment.location', string='To Location',
                                               domain="[('warehouse_id', '=', destination_warehouse_id)]")
    responsible_id = fields.Many2one('res.users', string='Responsible', default=lambda s: s.env.user)
    remarks = fields.Char(string='Remarks')

    def action_transfer(self):
        self.ensure_one()
        if self.quantity <= 0:
            raise UserError(_('Transfer quantity must be greater than zero.'))
        if self.source_warehouse_id == self.destination_warehouse_id and \
                self.source_location_id == self.destination_location_id:
            raise UserError(_('Source and destination location must be different.'))

        ref = self.env['ir.sequence'].next_by_code('garment.stock.transfer') or _('New')
        Move = self.env['garment.stock.move']
        move_out = Move.create({
            'material_id': self.material_id.id,
            'warehouse_id': self.source_warehouse_id.id,
            'location_id': self.source_location_id.id,
            'destination_warehouse_id': self.destination_warehouse_id.id,
            'destination_location_id': self.destination_location_id.id,
            'move_type': 'transfer_out',
            'quantity': self.quantity,
            'reference': ref,
            'remarks': self.remarks,
        })
        move_in = Move.create({
            'material_id': self.material_id.id,
            'warehouse_id': self.destination_warehouse_id.id,
            'location_id': self.destination_location_id.id,
            'move_type': 'transfer_in',
            'quantity': self.quantity,
            'reference': ref,
            'remarks': self.remarks,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Transfer Moves'),
            'res_model': 'garment.stock.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', [move_out.id, move_in.id])],
        }
