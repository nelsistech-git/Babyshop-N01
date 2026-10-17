# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import api, models


class ReportBondGeneric(models.AbstractModel):
    _name = 'report.nelsis_bond_reconciliation.report_bond_generic'
    _description = 'Bond Generic Management Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizards = self.env['bond.warehouse.report.wizard'].browse(docids)
        return {
            'doc_ids': wizards.ids,
            'doc_model': 'bond.warehouse.report.wizard',
            'docs': wizards,
            'reports': {w.id: w._get_report_data() for w in wizards},
            'fmt': wizards[:1].fmt_cell if wizards else str,
            'is_num': wizards[:1].is_number if wizards else bool,
        }
