# coding=utf-8
from odoo import models, api


class HREmployeeRequisitionPrint(models.AbstractModel):
    """ HR Employee Requisition Print Report """

    _name = 'report.custom_hr_employee_requisition.hr_emp_rec_print_qweb'
    _description = 'HR Employee Requisition Print Report'

    # @api.model
    # def _get_report_values(self, docids, data=None):
    #     """ Render report with sql
    #         @:param docids
    #         @:param data
    #      """
    #     report_obj = self.env['report']
    #     report = report_obj._get_report_from_name('custom_hr_employee_requisition.hr_emp_rec_print')
    #     docargs = {
    #         'doc_ids': docids,
    #         'doc_model': report.model,
    #         'docs': data['ids'],
    #         'other': data['other'],
    #     }
    #     return report_obj.render('custom_hr_employee_requisition.hr_emp_rec_print', docargs)

    # @api.model
    # def _get_report_values(self, docids, data=None):
    #     docs = self.env['hr.employee.requisition'].browse(docids)
    #     return {
    #         'doc_ids': docs.ids,
    #         'doc_model': 'hr.employee.requisition',
    #         'data': data['ids'],
    #         'other': data['other'],
    #         'docs': docs,
    #     }



    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Generate the report values based on the document IDs.
        """
        if not docids:
            # Fallback to active_ids from the context if docids is empty
            docids = self.env.context.get('active_ids', [])
        requisition = self.env['hr.employee.requisition'].browse(docids)

        # Check if the requisition exists
        if not requisition.exists():
            _logger.error("The requisition record with ID %s does not exist.", docids[0])
            raise ValueError("The requisition record with ID %s does not exist." % docids[0])

        # Execute SQL query to get additional requisition details
        requisition_sql = """
            SELECT
              emr.id AS id,
        COALESCE(emr.rec_no, 'N/A') AS requisition_no,
        COALESCE(hd.name->>'en_US', 'Unknown') AS department, 
        COALESCE(hj.name->>'en_US', 'Unknown') AS designation,
        COALESCE(emr.position_type, 'Not specified') AS position_type,
        COALESCE(emr.contract_type_id, 0) AS contract_type_id,
        COALESCE(emr.gender, 'Not specified') AS gender,
        COALESCE(emr.date, '1900-01-01') AS date,
        COALESCE(emr.approved_man, 0) AS approved_man,
        COALESCE(emr.actual_man, 0) AS actual_man,
        COALESCE(emr.request_man, 0) AS request_man,
        COALESCE(emr.est_salary, 0) AS est_salary,
        COALESCE(emr.act_salary, 0) AS act_salary,
        COALESCE(emr.expertise, 'Not specified') AS expertise,
        COALESCE(emr.exp_year, 0) AS exp_year,
        COALESCE(emr.edu_qual, 'Not specified') AS edu_qual,
        COALESCE(emr.requirements, 'None') AS requirements,
        COALESCE(emr.is_parttime, FALSE) AS is_parttime,
        COALESCE(emr.is_desc_exist, FALSE) AS is_desc_exist,
        COALESCE(emr.is_reduce_mp, FALSE) AS is_reduce_mp,
        COALESCE(emr.is_fucn_effective, FALSE) AS is_fucn_effective,
        COALESCE(emr.is_cost_reduce, FALSE) AS is_cost_reduce,
        COALESCE(emr.is_internal, FALSE) AS is_internal,
        COALESCE(emr.prospects, 'Not specified') AS prospects,
        COALESCE(emr.investigations, 'Not specified') AS investigations,
        COALESCE(emr.commencement_date, '1900-01-01') AS commencement_date,
        COALESCE(emr.have_mobile_allowance, FALSE) AS have_mobile_allowance,
        COALESCE(emr.need_computer, FALSE) AS need_computer,
        COALESCE(emr.proposed_salary, 0) AS proposed_salary,
        COALESCE(emr.have_travel_allowance, FALSE) AS have_travel_allowance,
        COALESCE(emr.need_lunch, FALSE) AS need_lunch,
        COALESCE(emr.other_benefits, 'None') AS other_benefits,
        COALESCE(hpp.name, 'Unknown') AS probation_name,
        COALESCE(emr.internal_transfer, FALSE) AS internal_transfer,
        COALESCE(emr.required_training, FALSE) AS required_training,
        COALESCE(hpp1.name, 'Unknown') AS training_name,
        COALESCE(emr.training_details, 'Not specified') AS training_details,
        COALESCE(hj1.name->>'en_US', 'Unknown') AS requested_designation,
        COALESCE(hj2.name->>'en_US', 'Unknown') AS authorized_designation,
        COALESCE(hj3.name->>'en_US', 'Unknown') AS recommended_designation,
        COALESCE(hj4.name->>'en_US', 'Unknown') AS approved_designation
            FROM 
                hr_employee_requisition AS emr
                LEFT JOIN hr_department AS hd ON hd.id = emr.rec_dept
                LEFT JOIN hr_job AS hj ON hj.id = emr.rec_position
                LEFT JOIN hr_probation_period AS hpp ON hpp.id = emr.probation_period_id
                LEFT JOIN hr_probation_period AS hpp1 ON hpp1.id = emr.training_duration_id
                LEFT JOIN hr_employee AS em ON em.id = emr.requested_by
                LEFT JOIN hr_job AS hj1 ON hj1.id = emr.requested_designation
                LEFT JOIN hr_employee AS em2 ON em2.id = emr.authorized_by
                LEFT JOIN hr_job AS hj2 ON hj2.id = emr.authorized_designation
                LEFT JOIN hr_employee AS em3 ON em3.id = emr.recommended_by
                LEFT JOIN hr_job AS hj3 ON hj3.id = emr.recommended_designation
                LEFT JOIN hr_employee AS em4 ON em4.id = emr.approved_by
                LEFT JOIN hr_job AS hj4 ON hj4.id = emr.approved_designation
            WHERE emr.id = %s
            LIMIT 1
        """ % docids[0]
        print("docids",docids[0],docids)
        self.env.cr.execute(requisition_sql)
        result = self.env.cr.dictfetchall()

        # Prepare data for the report
        data = {
            'ids': result,
            'other': {
                'form_no': requisition.rec_no if requisition.rec_no else 'N/A',
                'requisition_dept': requisition.rec_dept.name if requisition.rec_dept else 'Unknown',
                'requisition_company': requisition.company_id.name if requisition.company_id else 'Unknown',
            },
            'company': requisition.company_id
        }

        context = dict(self.env.context)
        context.update({'company': self.env.company})
        context.update({'company_name': self.env.company.name})
        context.update({'company_street': self.env.company.street})
        context.update({'company_street2': self.env.company.street2})
        context.update({'company_city': self.env.company.city})
        context.update({'company_zip': self.env.company.zip})
        context.update({'company_phone': self.env.company.phone})
        context.update({'company_website': self.env.company.website})
        print("context",context)
        test = {
            'context': context,
            'doc_ids': requisition.ids,
            'doc_model': 'hr.employee.requisition',
            'data': data['ids'],
            'other': data['other'],
            'docs': requisition,
        }

        print("test",test)
        return {
            'context': context,
            'doc_ids': requisition.ids,
            'doc_model': 'hr.employee.requisition',
            'data': data['ids'],
            'other': data['other'],
            'docs': requisition,
        }
