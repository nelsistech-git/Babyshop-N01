# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateRequisitionLine(models.Model):
    _name = 'real.estate.requisition.line'
    _description = 'Real Estate Requisition Line'
    _order = 'id'

    requisition_id = fields.Many2one('real.estate.requisition', string='Requisition',
                                      required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity', digits=(12, 2), required=True, default=1.0)
    uom_id = fields.Many2one('uom.uom', string='UOM')
    estimated_rate = fields.Monetary(string='Estimated Rate')
    estimated_amount = fields.Monetary(string='Estimated Amount', compute='_compute_amount', store=True)
    available_stock = fields.Float(
        string='Available Stock', digits=(12, 2),
        help='Informational only in this phase; live stock-on-hand '
             'integration is wired up once the Inventory dependency is '
             'added in a later phase.')
    requested_quantity = fields.Float(string='Requested Quantity', digits=(12, 2),
                                       compute='_compute_requested_quantity', store=True)

    currency_id = fields.Many2one(related='requisition_id.currency_id', readonly=True)

    @api.depends('quantity', 'estimated_rate')
    def _compute_amount(self):
        for rec in self:
            rec.estimated_amount = rec.quantity * rec.estimated_rate

    @api.depends('quantity')
    def _compute_requested_quantity(self):
        for rec in self:
            rec.requested_quantity = rec.quantity

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.display_name
            self.uom_id = self.product_id.uom_id
            self.estimated_rate = self.product_id.standard_price
