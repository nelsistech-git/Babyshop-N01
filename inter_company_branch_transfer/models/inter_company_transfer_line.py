# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class InterCompanyTransferLine(models.Model):
    _name = 'inter.company.transfer.line'
    _description = 'Inter-Company Transfer Line'

    transfer_id = fields.Many2one(
        'inter.company.transfer', string='Transfer', required=True,
        ondelete='cascade', index=True)
    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
        domain="[('type', 'in', ('product', 'consu'))]")
    product_uom_qty = fields.Float(
        string='Quantity', required=True, default=1.0)
    product_uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure', required=True)

    source_company_id = fields.Many2one(
        related='transfer_id.source_company_id', string='Source Company', store=True)
    dest_company_id = fields.Many2one(
        related='transfer_id.dest_company_id', string='Destination Company', store=True)

    qty_delivered = fields.Float(
        string='Delivered', compute='_compute_qty_delivered',
        help='Quantity actually shipped from the source warehouse (from the '
             'linked Delivery Order).')
    qty_received = fields.Float(
        string='Received', compute='_compute_qty_received',
        help='Quantity actually received into the destination warehouse '
             '(from the linked Receipt).')

    @api.depends('transfer_id.picking_id.move_ids.quantity',
                 'transfer_id.picking_id.move_ids.state')
    def _compute_qty_delivered(self):
        for line in self:
            picking = line.transfer_id.picking_id
            qty = 0.0
            if picking:
                moves = picking.move_ids.filtered(
                    lambda m: m.product_id == line.product_id and m.state == 'done')
                qty = sum(moves.mapped('quantity'))
            line.qty_delivered = qty

    @api.depends('transfer_id.receipt_id.move_ids.quantity',
                 'transfer_id.receipt_id.move_ids.state')
    def _compute_qty_received(self):
        for line in self:
            picking = line.transfer_id.receipt_id
            qty = 0.0
            if picking:
                moves = picking.move_ids.filtered(
                    lambda m: m.product_id == line.product_id and m.state == 'done')
                qty = sum(moves.mapped('quantity'))
            line.qty_received = qty

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.product_uom_id = line.product_id.uom_id

    @api.constrains('product_uom_qty')
    def _check_quantity(self):
        for line in self:
            if line.product_uom_qty <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))
