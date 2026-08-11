# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResCompany(models.Model):
    """Extra branch-level metadata that the thermal receipt needs.

    These fields live on res.company so that every branch (modelled as a
    separate company / multi-company record in Odoo) carries its own
    trading name, BIN, shop location and receipt notes. They are loaded
    into the POS session at load_pos_data time by Odoo core and cached in
    IndexedDB automatically - so the branch header stays correct even
    while the POS is running offline.
    """
    _inherit = "res.company"

    pos_trading_name = fields.Char(
        string="POS Trading Name",
        help="Name printed on the receipt header (e.g. 'BABY SHOP LTD'). "
             "Falls back to the company name if left empty.",
    )
    pos_shop_line = fields.Char(
        string="POS Shop / Floor Line",
        help="Secondary address line, e.g. 'Shop no-4, Block-D, Level-1'.",
    )
    pos_bin_no = fields.Char(
        string="BIN Registration No.",
        help="Business Identification Number printed on the receipt, "
             "e.g. '002265729-0401'.",
    )
    pos_branch_code = fields.Char(
        string="Branch Code",
        help="Short branch code used to build the invoice number prefix, "
             "e.g. 'UTT' for Uttara. Defaults to the first 3 letters of "
             "the company name if left empty.",
    )
    pos_return_policy = fields.Text(
        string="POS Receipt Return Policy",
        default="Can be exchanged within 7 days. No refund.",
        help="Printed above the footer on every receipt.",
    )
    pos_receipt_footer_note = fields.Char(
        string="POS Receipt Footer Note",
        default="Thank you for shopping with us!",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        # Ship the branch metadata down to the POS frontend / IndexedDB
        # cache so the header renders correctly even offline.
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list += [
            "pos_trading_name",
            "pos_shop_line",
            "pos_bin_no",
            "pos_branch_code",
            "pos_return_policy",
            "pos_receipt_footer_note",
            "vat",
            "street",
            "street2",
            "city",
            "phone",
        ]
        return fields_list
