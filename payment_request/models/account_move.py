# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_vat_challan_no = fields.Char(
        string='VAT Challan No', copy=False, tracking=True,
        help="Supplier's VAT challan number for this bill. Synced automatically to the Payment "
             "Requisition line and printed on Mushak 6.6 (সংশ্লিষ্ট কর চালানপত্র - নম্বর).")
    x_vat_challan_date = fields.Date(
        string='VAT Challan Date', copy=False, tracking=True,
        help="Issue date of the supplier's VAT challan. Synced automatically to the Payment "
             "Requisition line and printed on Mushak 6.6 (সংশ্লিষ্ট কর চালানপত্র - ইস্যুর তারিখ).")

    x_due_date_calc = fields.Date(
        string='Due Date (Calculated)', compute='_compute_x_due_date_calc', store=True,
        help="Bill Date + the Payment Terms days (the latest instalment if the term has several). "
             "Odoo hides the standard Due Date field as soon as a Payment Term is set; this "
             "read-only copy stays visible and can be used for tracking, filters and reports. "
             "Empty until the Bill Date is entered (a draft without a Bill Date would otherwise "
             "be counted from today).")

    @api.depends('invoice_date_due', 'invoice_date', 'invoice_payment_term_id', 'state', 'move_type')
    def _compute_x_due_date_calc(self):
        for move in self:
            if move.is_invoice(include_receipts=True) and (move.invoice_date or move.state != 'draft'):
                move.x_due_date_calc = move.invoice_date_due
            else:
                move.x_due_date_calc = False