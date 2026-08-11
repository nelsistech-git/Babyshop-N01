# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SaleOrderReceipt(models.Model):
    """Billing/receipt-only fields for the Express POS thermal receipt reports
    (Bangladesh and Dubai/UAE layouts). Kept in its own file, separate from the
    main checkout logic in sale_order.py, so the printing math is easy to audit
    on its own.

    Design note on "Receive / Exchange / Mode of Payment": rather than trying
    to reverse-engineer what was tendered from invoice/payment reconciliation
    at print time (fragile - depends on invoicing/payment timing and internal
    widget fields that can change between Odoo versions), the two tender
    fields below are written once, directly, by action_express_pos_checkout()
    in sale_order.py at the moment the sale actually happens. Everything else
    (gross amount, discount, tax rate) is fully derivable from the order lines
    and totals at any time, so those stay as plain compute fields.
    """
    _name = 'sale.order'
    _inherit = 'sale.order'

    # -- Written once by action_express_pos_checkout(); not shown on any form,
    #    used only to feed the compute fields below. --
    express_pos_checkout_amount_paid = fields.Monetary(copy=False, default=0.0)
    express_pos_checkout_payment_methods = fields.Char(copy=False)

    express_receipt_gross_amount = fields.Monetary(
        string='Gross Amount (Before Discount)', compute='_compute_express_receipt_line_amounts')
    express_receipt_discount_amount = fields.Monetary(
        string='Total Discount Amount', compute='_compute_express_receipt_line_amounts')
    express_receipt_tax_rate = fields.Float(
        string='Effective Tax Rate %', compute='_compute_express_receipt_line_amounts')

    express_receipt_amount_paid = fields.Monetary(
        string='Amount Received', compute='_compute_express_receipt_payment_info')
    express_receipt_amount_change = fields.Monetary(
        string='Change Returned', compute='_compute_express_receipt_payment_info')
    express_receipt_payment_methods = fields.Char(
        string='Payment Mode(s)', compute='_compute_express_receipt_payment_info')

    @api.depends('order_line.product_uom_qty', 'order_line.price_unit', 'order_line.discount',
                 'amount_untaxed', 'amount_tax')
    def _compute_express_receipt_line_amounts(self):
        for order in self:
            gross = 0.0
            discount_amount = 0.0
            for line in order.order_line.filtered(lambda l: not l.display_type):
                line_gross = line.product_uom_qty * line.price_unit
                gross += line_gross
                discount_amount += line_gross * (line.discount or 0.0) / 100.0
            order.express_receipt_gross_amount = gross
            order.express_receipt_discount_amount = discount_amount
            order.express_receipt_tax_rate = round(
                (order.amount_tax / order.amount_untaxed) * 100.0, 2) if order.amount_untaxed else 0.0

    @api.depends('express_pos_checkout_amount_paid', 'express_pos_checkout_payment_methods',
                 'amount_total', 'state', 'invoice_ids.amount_total', 'invoice_ids.amount_residual',
                 'invoice_ids.state', 'invoice_ids.move_type')
    def _compute_express_receipt_payment_info(self):
        for order in self:
            paid = order.express_pos_checkout_amount_paid
            methods = order.express_pos_checkout_payment_methods
            if not paid:
                # Fallback for orders confirmed/invoiced outside the Express POS
                # checkout wizard (e.g. a normal quotation confirmed manually):
                # amount actually settled on posted customer invoices is always
                # (invoice total - invoice balance due), which needs no fragile
                # widget parsing.
                invoices = order.invoice_ids.filtered(
                    lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
                if invoices:
                    paid = sum(inv.amount_total - inv.amount_residual for inv in invoices)
                elif order.state in ('sale', 'done'):
                    paid = order.amount_total
            order.express_receipt_amount_paid = paid
            order.express_receipt_amount_change = max(0.0, paid - order.amount_total)
            if methods:
                order.express_receipt_payment_methods = methods
            elif paid + 0.005 < order.amount_total:
                order.express_receipt_payment_methods = _('Due / Credit')
            else:
                order.express_receipt_payment_methods = _('Cash')

    def _get_express_receipt_format(self):
        """Resolve which printed layout to use: an explicit override (from the
        "Print Receipt - Dubai/UAE" or "- Bangladesh" actions), else the
        branch setting, else the company-wide default, else 'bd'.
        """
        self.ensure_one()
        forced = self.env.context.get('express_receipt_force_format')
        if forced in ('bd', 'dubai'):
            return forced
        if self.express_pos_branch_id and self.express_pos_branch_id.receipt_format:
            return self.express_pos_branch_id.receipt_format
        return self.company_id.express_pos_default_receipt_format or 'bd'
