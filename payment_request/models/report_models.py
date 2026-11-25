# -*- coding: utf-8 -*-
"""Report models: run the same checks whether the PDF is printed from the form
buttons or from the form's Print menu."""
from odoo import api, models


class ReportRtgs(models.AbstractModel):
    _name = 'report.payment_request.report_rtgs_document'
    _description = 'RTGS Application Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['payment.request'].browse(docids)
        docs._check_can_print_rtgs()
        return {'doc_ids': docids, 'doc_model': 'payment.request', 'docs': docs, 'data': data}


class ReportBeftn(models.AbstractModel):
    _name = 'report.payment_request.report_beftn_document'
    _description = 'BEFTN Letter Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['payment.request'].browse(docids)
        docs._check_can_print_beftn()
        for rec in docs:
            rec._ensure_beftn_ref()
        return {'doc_ids': docids, 'doc_model': 'payment.request', 'docs': docs, 'data': data}


class ReportMushak66(models.AbstractModel):
    _name = 'report.payment_request.report_mushak66_document'
    _description = 'Mushak 6.6 VDS Certificate Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['payment.request'].browse(docids)
        docs._check_can_print_mushak66()
        return {'doc_ids': docids, 'doc_model': 'payment.request', 'docs': docs, 'data': data}
