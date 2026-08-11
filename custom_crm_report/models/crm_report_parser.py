# -*- coding: utf-8 -*-
from odoo import models, api


class ReportCrmReport(models.AbstractModel):
    _name = 'report.custom_crm_report.report_crm_report_template'
    _description = 'CRM Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['crm.report.wizard'].browse(docids)
        leads = wizard._get_leads()
        return {
            'docs': wizard,
            'leads': leads,
        }
