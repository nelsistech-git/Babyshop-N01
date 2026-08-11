from odoo import models, api


class HRApplicantReport(models.AbstractModel):
    """ HR Application Form Print Report """

    _name = 'report.custom_hr_recruitment.report_hr_applicant_qweb'
    _template = 'custom_hr_recruitment.report_hr_applicant_qweb'
    _description = 'HR Application Form Print Report'

    @api.model
    def render_html(self, docids, data=None):
        """ Render report with sql
            @:param docids
            @:param data
         """
        report_obj = self.env['report']
        report = report_obj._get_report_from_name(self._template)

        Applicant = self.env['hr.applicant']
        selected_applicant = Applicant.browse(data['ids'])
        docargs = {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': selected_applicant
        }
        return report_obj.render(self._template, docargs)

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['hr.applicant'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.applicant',
            # 'data': data['ids'],
            # 'other': data['other'],
            'docs': docs,
        }
