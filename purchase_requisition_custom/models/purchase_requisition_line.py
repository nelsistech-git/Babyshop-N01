# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseRequisitionLine(models.Model):
    _name = 'purchase.requisition.line'
    _description = 'Purchase Requisition Line'
    _order = 'id'

    requisition_id = fields.Many2one(
        'purchase.requisition.custom',
        string='Requisition',
        required=True,
        ondelete='cascade',
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
    )

    # ─── Product Info (Inventory থেকে) ───────────────────────────────────
    product_id = fields.Many2one(
        'product.product',
        string='Product Name',
        required=True,
        domain="[('type', 'in', ['product', 'consu'])]",
    )
    product_type = fields.Char(
        string='Product Type',
        compute='_compute_product_info',
        store=True,
    )
    product_code = fields.Char(
        string='Product Code',
        compute='_compute_product_info',
        store=True,
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit',
        compute='_compute_product_info',
        store=True,
        readonly=False,
    )
    present_stock = fields.Float(
        string='Product Stock',
        compute='_compute_present_stock',
        store=True,
        digits='Product Unit of Measure',
    )

    # ─── Last Purchase Info (Purchase Orders থেকে) ────────────────────────
    last_purchase_price = fields.Float(
        string='Last Product Price',
        digits='Product Price',
        compute='_compute_last_purchase_info',
        store=True,
        readonly=False,
    )
    last_purchase_qty = fields.Float(
        string='Last Purchase Quantity',
        digits='Product Unit of Measure',
        compute='_compute_last_purchase_info',
        store=True,
        readonly=False,
    )
    last_receive_date = fields.Date(
        string='Last Purchase Date',
        compute='_compute_last_purchase_info',
        store=True,
        readonly=False,
    )

    # ─── Request / Rate / Amount ──────────────────────────────────────────
    quantity = fields.Float(
        string='Request Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure',
    )
    rate = fields.Float(
        string='Rate',
        digits='Product Price',
        compute='_compute_rate',
        store=True,
        readonly=False,
    )
    amount = fields.Float(
        string='Amount',
        compute='_compute_amount',
        store=True,
        digits='Product Price',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency',
        store=True,
    )
    notes = fields.Text(string='Notes')

    # ─────────────────────────────────────────────────────────────────────
    # COMPUTE
    # ─────────────────────────────────────────────────────────────────────

    @api.depends('requisition_id', 'requisition_id.currency_id')
    def _compute_currency(self):
        for line in self:
            if line.requisition_id and line.requisition_id.currency_id:
                line.currency_id = line.requisition_id.currency_id
            else:
                line.currency_id = self.env.company.currency_id

    @api.depends('product_id')
    def _compute_product_info(self):
        for line in self:
            if line.product_id:
                tmpl = line.product_id.product_tmpl_id
                line.uom_id = line.product_id.uom_id
                type_map = {
                    'product': 'Storable',
                    'consu': 'Consumable',
                    'service': 'Service',
                }
                line.product_type = type_map.get(tmpl.type, tmpl.type)
                line.product_code = tmpl.default_code or ''
            else:
                line.uom_id = False
                line.product_type = ''
                line.product_code = ''

    @api.depends('product_id')
    def _compute_present_stock(self):
        for line in self:
            if line.product_id:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id.usage', '=', 'internal'),
                ])
                line.present_stock = sum(quants.mapped('quantity'))
            else:
                line.present_stock = 0.0

    @api.depends('product_id')
    def _compute_last_purchase_info(self):
        for line in self:
            if line.product_id:
                domain = [
                    ('product_id', '=', line.product_id.id),
                    ('order_id.state', 'in', ['purchase', 'done']),
                ]
                last_po_line = self.env['purchase.order.line'].search(
                    domain, order='order_id desc', limit=1,
                )
                if last_po_line:
                    line.last_purchase_price = last_po_line.price_unit
                    line.last_purchase_qty = last_po_line.product_qty
                    line.last_receive_date = (
                        last_po_line.order_id.date_order.date()
                        if last_po_line.order_id.date_order
                        else False
                    )
                    line.vendor_id = last_po_line.order_id.partner_id.id
                else:
                    line.last_purchase_price = line.product_id.standard_price
                    line.last_purchase_qty = 0.0
                    line.last_receive_date = False
                    line.vendor_id = False
            else:
                line.last_purchase_price = 0.0
                line.last_purchase_qty = 0.0
                line.last_receive_date = False
                line.vendor_id = False

    @api.depends('last_purchase_price')
    def _compute_rate(self):
        for line in self:
            line.rate = line.last_purchase_price

    @api.depends('quantity', 'rate')
    def _compute_amount(self):
        for line in self:
            line.amount = line.quantity * line.rate

    # ─────────────────────────────────────────────────────────────────────
    # ONCHANGE
    # ─────────────────────────────────────────────────────────────────────

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # Stock
            quants = self.env['stock.quant'].search([
                ('product_id', '=', self.product_id.id),
                ('location_id.usage', '=', 'internal'),
            ])
            self.present_stock = sum(quants.mapped('quantity'))
            self.uom_id = self.product_id.uom_id

            # Product Type & Code
            tmpl = self.product_id.product_tmpl_id
            type_map = {
                'product': 'Storable',
                'consu': 'Consumable',
                'service': 'Service',
            }
            self.product_type = type_map.get(tmpl.type, tmpl.type)
            self.product_code = tmpl.default_code or ''

            # Last Purchase Info + Vendor auto set
            domain = [
                ('product_id', '=', self.product_id.id),
                ('order_id.state', 'in', ['purchase', 'done']),
            ]
            last_po_line = self.env['purchase.order.line'].search(
                domain, order='order_id desc', limit=1,
            )
            if last_po_line:
                self.last_purchase_price = last_po_line.price_unit
                self.last_purchase_qty = last_po_line.product_qty
                self.last_receive_date = (
                    last_po_line.order_id.date_order.date()
                    if last_po_line.order_id.date_order
                    else False
                )
                self.vendor_id = last_po_line.order_id.partner_id.id
                self.rate = last_po_line.price_unit
            else:
                self.last_purchase_price = self.product_id.standard_price
                self.last_purchase_qty = 0.0
                self.last_receive_date = False
                self.vendor_id = False
                self.rate = self.product_id.standard_price
        else:
            self.present_stock = 0.0
            self.product_type = ''
            self.product_code = ''
            self.last_purchase_price = 0.0
            self.last_purchase_qty = 0.0
            self.last_receive_date = False
            self.vendor_id = False
            self.rate = 0.0
            self.uom_id = False