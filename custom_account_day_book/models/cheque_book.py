from odoo import models, fields, api,_
from odoo.exceptions import AccessError


class ChequeReportSettings(models.Model):
    _name = "report.configuration"
    _description = "Report configuration"

    branch_name = fields.Char(string='Branch Name')
    account_no = fields.Char(string='Account Number')
    company_name = fields.Char(string='Company Name')

    @api.constrains('branch_name')
    def _check_single_cheque_report_settings(self):
        envobj = self.env['report.configuration'].search([])
        if len(envobj) > 1:
            raise AccessError(
                _("Warning! You cannot save data more than once.")
            )

    def print_report(self):
        self.env.cr.execute(
            """ SELECT branch_name, account_no, company_name FROM report_configuration order by id asc limit 1 """)
        data_list = self.env.cr.fetchone()
        if data_list == None:
            branch_name = ''
            account_no = ''
            company_name = ''
        else:
            branch_name = data_list[0]
            account_no = data_list[1]
            company_name = data_list[2]
        data = {
            'model': "report.configuration",
            'branch_name': branch_name,
            'account_no': account_no,
            'company_name': company_name,
        }
        return self.env.ref('custom_account_day_book.cheque_report').with_context(
            landscape=True).report_action(self, data=data)

