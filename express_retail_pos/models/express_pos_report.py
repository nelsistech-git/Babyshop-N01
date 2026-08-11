# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class ExpressPosSalesReport(models.Model):
    """SQL-view analysis model behind Reporting > Sales Analysis.
    One row per sale order line coming from the Checkout Console, denormalized
    with the branch/brand/category/cashier dimensions cashiers and management
    actually want to slice by. Read-only, non-editable, security-rule scoped
    exactly like sale.order (the underlying ir.rule on sale.order is honoured
    through the join), so a Branch Manager only ever sees their own branch here.
    """
    _name = 'express.pos.sales.report'
    _description = 'Express POS Sales Analysis'
    _auto = False
    _order = 'date_order desc'
    _rec_name = 'order_id'

    order_id = fields.Many2one('sale.order', string='Order', readonly=True)
    order_line_id = fields.Many2one('sale.order.line', string='Order Line', readonly=True)
    date_order = fields.Datetime(string='Order Date', readonly=True)
    state = fields.Selection([
        ('draft', 'Held / Draft'), ('sent', 'Quotation Sent'),
        ('sale', 'Completed'), ('done', 'Locked'), ('cancel', 'Cancelled'),
    ], readonly=True)
    branch_id = fields.Many2one('express.pos.branch', string='Branch/Showroom', readonly=True)
    brand_id = fields.Many2one('express.pos.brand', string='Brand', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    user_id = fields.Many2one('res.users', string='Cashier', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    loyalty_card_id = fields.Many2one('express.loyalty.card', string='Loyalty Card', readonly=True)
    is_offer_line = fields.Boolean(string='Auto Offer/Discount Line', readonly=True)
    qty = fields.Float(string='Quantity', readonly=True)
    price_unit = fields.Monetary(string='Unit Price', readonly=True)
    discount = fields.Float(string='Discount %', readonly=True)
    price_subtotal = fields.Monetary(string='Untaxed Amount', readonly=True)
    price_total = fields.Monetary(string='Total Amount', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    order_count = fields.Integer(string='# Orders', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    sol.id AS id,
                    sol.id AS order_line_id,
                    so.id AS order_id,
                    so.date_order AS date_order,
                    so.state AS state,
                    so.express_pos_branch_id AS branch_id,
                    so.express_pos_brand_id AS brand_id,
                    so.company_id AS company_id,
                    so.partner_id AS partner_id,
                    so.user_id AS user_id,
                    so.loyalty_card_id AS loyalty_card_id,
                    sol.product_id AS product_id,
                    pt.categ_id AS categ_id,
                    sol.express_pos_is_offer_line AS is_offer_line,
                    sol.product_uom_qty AS qty,
                    sol.price_unit AS price_unit,
                    sol.discount AS discount,
                    sol.price_subtotal AS price_subtotal,
                    sol.price_total AS price_total,
                    so.currency_id AS currency_id,
                    1 AS order_count
                FROM sale_order_line sol
                JOIN sale_order so ON so.id = sol.order_id
                LEFT JOIN product_product pp ON pp.id = sol.product_id
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE so.is_express_pos = true
                AND sol.display_type IS NULL
            )
        """)


class ReportExpressPosReceipt(models.AbstractModel):
    _name = 'report.express_retail_pos.report_express_pos_receipt_document'
    _description = 'Express POS Thermal Receipt Report Values'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['sale.order'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': docs,
            'is_duplicate': self.env.context.get('is_duplicate', False),
        }