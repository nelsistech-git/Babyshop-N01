# coding=utf-8
from odoo import models, api


class EmployeeLetterWithoutLetterHead(models.AbstractModel):
    """ Employee Letter Head report without Letter head """
    _name = 'report.custom_hr_employee_letters.emp_letter_wo_report_qweb'
    _description = 'Employee Letter Without Letter Head'

    # def render_html(self, docids, data=None):
    #     report_obj = self.env['report']
    #     report = report_obj._get_report_from_name('custom_hr_employee_letters.emp_letter_wo_report_qweb')
    #     docargs = {
    #         'doc_ids': docids,
    #         'doc_model': report.model,
    #         'docs': data['ids'],
    #     }
    #     return report_obj.render('custom_hr_employee_letters.emp_letter_wo_report_qweb', docargs)

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['hr.employee.letters'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.employee.letters',
            'data': data['ids'],
            'docs': docs,
        }
