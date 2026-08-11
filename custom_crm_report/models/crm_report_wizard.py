# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime


class CrmReportWizard(models.TransientModel):
    _name = 'crm.report.wizard'
    _description = 'CRM Report Wizard'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    salesperson_id = fields.Many2one('res.users', string='Salesperson')

    def _get_leads(self):
        domain = []
        if self.date_from:
            domain.append(('create_date', '>=', datetime.combine(self.date_from, datetime.min.time())))
        if self.date_to:
            domain.append(('create_date', '<=', datetime.combine(self.date_to, datetime.max.time())))
        if self.salesperson_id:
            domain.append(('user_id', '=', self.salesperson_id.id))
        return self.env['crm.lead'].search(domain)

    def action_print_report(self):
        return self.env.ref('custom_crm_report.action_crm_report_pdf').report_action(self)
