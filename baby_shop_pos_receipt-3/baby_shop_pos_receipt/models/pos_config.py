# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    receipt_paper_width = fields.Selection(
        [("80mm", "80mm"), ("58mm", "58mm")],
        string="Thermal Paper Width",
        default="80mm",
        help="Controls the print CSS width applied to the receipt "
             "(monospace font, zero page margins).",
    )
    receipt_branch_code = fields.Char(
        string="Receipt Branch Code Override",
        help="Overrides the company's Branch Code for this POS/shop only. "
             "Leave empty to use res.company.pos_branch_code.",
    )
    receipt_show_barcode = fields.Boolean(
        string="Show Barcode on Receipt",
        default=True,
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        # Make sure the new config fields reach the frontend POS store.
        fields_list = super()._load_pos_data_fields(config_id)
        fields_list += [
            "receipt_paper_width",
            "receipt_branch_code",
            "receipt_show_barcode",
        ]
        return fields_list
