from odoo import models, fields, api, _
import datetime
from datetime import datetime
from itertools import groupby
#
# try:
#     from odoo.tools.misc import xlsxwriter
# except ImportError:
#     from odoo.addons.helper import xlsxwriter
#
# import base64
# from io import BytesIO


class FringeBenefitsReportWizard(models.Model):
    _name = 'fringe.benefits.report.wizard'
    _description = 'Fringe Benefits Report Wizard'

    file_data = fields.Binary('Fringe Benefits Report')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Location', default=lambda self: self._get_work_loc(),
                                  domain=lambda self: self._set_domain_work_loc())
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    category_ids = fields.Many2many('hr.employee.category', 'fringe_benefits_employee_category_rel', 
                'selected_id', 'category_id', string='Tags')

    sbu_unit_id = fields.Many2one('hr.sbu.unit', string='Office/Business Unit')

    @api.model
    def _set_domain_work_loc(self):
        if self.env.user.user_work_location_id:
            return [('is_work_loc', '=', True), ('state', '=', 'done'),
                    ('id', '=', self.env.user.user_work_location_id.id)]
        else:
            return [('is_work_loc', '=', True), ('state', '=', 'done')]

    @api.model
    def _get_work_loc(self):
        if self.env.user.user_work_location_id:
            return self.env.user.user_work_location_id.id

    def fringe_benefits_report_pdf(self):
        employee_id = self.employee_id
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.fringe_benefits_report_sql(employee_id, department_id, user_work_location_id)

        return self.env.ref(
            'custom_hr_report.fringe_benefits_report_tmpl').with_context(landscape=False).report_action(self, data=data)

    @api.onchange('user_work_location_id', 'department_id')
    def _onchange_employees(self):
        domain = []

        if self.user_work_location_id:
            domain += [('user_work_location_id', '=', self.user_work_location_id.id)]

        if self.department_id:
            domain += [('department_id', '=', self.department_id.id)]

        return {'domain': {
            'employee_id': domain,
        }}

    def fringe_benefits_report_sql(self, employee_id, department_id, user_work_location_id):

        employeeFilter = ""
        departmentFilter = ""
        locationFilter = ""
        dept_name = "All"
        work_location_name = "All"
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "hre.name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "hre.id_card_no"
        print(order_by)

        if employee_id:
            employeeFilter = "AND hre.id = %s" % employee_id.id

        if department_id:
            departmentFilter = "AND hre.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            locationFilter = "AND hre.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND hre.sbu_unit_id = {0}".format(self.sbu_unit_id.id)  

        data_sql = """
                    SELECT hre.id_card_no AS id_no, hre.name AS emp_name, hrf.id as id, COALESCE(hre.user_work_location_id, 100000) AS user_work_location_id, sl.name AS location_name,
                    hrf.dept_name as assigned_dept, hp.name as particular, hrf.qty as particular_qty,hrf.value as paricular_value
                    FROM hr_facilities hrf
                    LEFT JOIN hr_employee hre ON hre.id = hrf.employee_id
                    LEFT JOIN stock_location sl ON sl.id = hre.user_work_location_id
                    LEFT JOIN hr_particulars hp ON hp.id = hrf.particular_id
                    {5} JOIN (
                            SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                            JOIN hr_employee_category etag on etag.id=ecr.category_id
                            {4}
                            GROUP BY emp_id
                        ) emp_tag ON emp_tag.emp_id = hre.id
                    WHERE (1=1) {0} {1} {2} {3}
                    -- ORDER BY hre.id_card_no, hre.name, hre.user_work_location_id, sl.name
                    ORDER BY {6}, hre.name, hre.user_work_location_id, sl.name
                    """.format(employeeFilter, departmentFilter,
                                locationFilter, business_unit_filter,
                                tags_filter, tag_filter_join,
                                order_by
                                )
        self.env.cr.execute(data_sql)
        data_list = self.env.cr.dictfetchall()
        # print(data_list)

        # define a fuction for key
        def key_func(k):
            return k['user_work_location_id']

        data_list = sorted(data_list, key=key_func)

        final_data_list = []

        # item_obj = self.env['hr.facilities'].browse(o['id'])
        # selection_name = dict(item_obj._fields['assigned_dept'].selection).get(item_obj.assigned_dept)

        for key, value in groupby(data_list, key_func):
            vals = {
                key: list(value)
            }
            final_data_list.append(vals)

        data = {
            'model': 'fringe.benefits.report.wizard',
            'form': self.read()[0],
            'csr': final_data_list,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }

        return data
