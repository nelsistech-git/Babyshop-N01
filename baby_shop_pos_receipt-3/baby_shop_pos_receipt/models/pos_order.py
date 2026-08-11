# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    receipt_invoice_no = fields.Char(
        string="Branch Invoice No.",
        compute="_compute_receipt_invoice_no",
        store=True,
        help="Human friendly branch invoice number, e.g. "
             "UTT/POS/2026/08/0145. Built from the branch code, the "
             "order date and the POS session sequence number, so it "
             "never collides across branches even when orders were "
             "created offline and synced later.",
    )

    @api.depends("session_id", "session_id.config_id", "sequence_number", "date_order")
    def _compute_receipt_invoice_no(self):
        for order in self:
            config = order.session_id.config_id
            company = config.company_id if config else order.company_id
            branch_code = (
                (config.receipt_branch_code if config else False)
                or (company.pos_branch_code if company else False)
                or (company.name[:3].upper() if company and company.name else "POS")
            )
            date_order = order.date_order or fields.Datetime.now()
            seq = order.sequence_number or 0
            order.receipt_invoice_no = "%s/POS/%s/%s/%04d" % (
                branch_code,
                date_order.strftime("%Y"),
                date_order.strftime("%m"),
                seq,
            )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list.append("receipt_invoice_no")
        return fields_list
