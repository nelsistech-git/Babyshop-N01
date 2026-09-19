# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwMaterialGrn(models.Model):
    _inherit = 'fw.material.grn'

    po_id = fields.Many2one('fw.purchase.order', string='Purchase Order',
                             help="Optional link to a Purchase Order created in FW "
                                  "Procurement. The existing PO Reference text field above "
                                  "remains available for GRNs without a system PO.")

    def action_confirm_inspection(self):
        result = super().action_confirm_inspection()
        pos = self.mapped('po_id')
        if pos:
            pos._recompute_receipt_state()
        return result
