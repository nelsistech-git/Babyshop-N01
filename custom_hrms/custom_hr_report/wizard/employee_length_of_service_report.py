from odoo import fields, models, api
from calendar import monthrange
from datetime import date
import datetime
from datetime import datetime
import xlsxwriter

import base64
from io import BytesIO


class EmployeeLengthOfServiceReportWizard(models.TransientModel):
    _name = "employee.length.of.service.report.wizard"
    _description = "Employee Length of Service Report"

    file_data = fields.Binary('Employee Length of Service Report')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       default=lambda self: self._get_work_loc(),
                                       domain=lambda self: self._set_domain_work_loc())
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')

    category_ids = fields.Many2many('hr.employee.category', 'length_of_service_employee_category_rel', 
                'selected_id', 'category_id', string='Tags')

    sbu_unit_id = fields.Many2one('hr.sbu.unit', string='Office/Business Unit')

    @api.model
    def _set_domain_work_loc(self):
        if self.env.user.user_work_location_id:
            return [('is_work_loc', '=', True), ('state', '=', 'done'), ('id', '=', self.env.user.user_work_location_id.id)]
        else:
            return [('is_work_loc', '=', True), ('state', '=', 'done')]

    @api.model
    def _get_work_loc(self):
        if self.env.user.user_work_location_id:
            return self.env.user.user_work_location_id.id

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

    def employee_length_of_service_report_excel(self):
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        # get data from sql
        data = self.employee_length_of_service_report_sql(user_work_location_id, department_id, employee_id)


        file_name = "Employee Length of Service Report (%s - %s).xlsx"
        file_pointer = BytesIO()

        workbook = xlsxwriter.Workbook(file_pointer)

        # main header formatting
        format0 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
        format0.set_align('center')
        format0.set_border()

        # column header formatting
        format1 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format1.set_align('left')
        format1.set_border()
        format2 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format2.set_align('center')
        format2.set_border()
        format3 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format3.set_align('right')
        format3.set_border()

        # body formatting
        format4 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format4.set_align('left')
        format4.set_border()
        format5 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format5.set_align('center')
        format5.set_border()
        format6 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format6.set_align('right')
        format6.set_border()

        # grand total formatting
        format7 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': True})
        format7.set_border()
        format8 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
        format8.set_border()
        format9 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
        format9.set_border()

        sheet = workbook.add_worksheet('Employee Length of Service Report')

        sheet.merge_range(0, 0, 0, 6, "{0}".format(data['form']['company_id'][1]), format0)

        sheet.merge_range(0, 0, 2, 6,
                          "Employee Length of Service Report",
                          format0)
        
        
        sheet.merge_range(3, 0, 3, 3, 'Work/Job Location: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Work/Job Location: All", format1)
        sheet.merge_range(4, 0, 4, 3, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)

        sheet.merge_range(3, 4, 3, 6, 'Department Name: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Department Name: All", format1)
        sheet.merge_range(4, 4, 4, 6, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)

        sheet.write(5, 0, 'Sl.', format2)
        sheet.write(5, 1, 'Employee ID', format2)
        sheet.write(5, 2, 'Employee Name', format2)
        sheet.write(5, 3, 'Joining Date', format2)
        sheet.write(5, 4, 'Designation', format2)
        sheet.write(5, 5, 'Work/Job Location', format2)
        sheet.write(5, 6, 'Service Period', format2)

        row = 6
        col = 0

        sl_no = 1
        for rec in data['csr']:
            new_col = 0
            sheet.write(row, col + new_col, sl_no, format5)
            new_col += 1
            sheet.write(row, col + new_col, rec['emp_id'], format4)
            new_col += 1
            sheet.write(row, col + new_col, rec['emp_name'], format5)
            new_col += 1

            # sheet.write(row, col + new_col, rec['emp_joining_date'], format4)
            print("date", rec['emp_joining_date'])
            sheet.write(row, col + new_col, str(rec['emp_joining_date']), format4)
            new_col += 1
            sheet.write(row, col + new_col, rec['department_name'], format4)
            new_col += 1
            sheet.write(row, col + new_col, rec['work_location_name'], format4)
            new_col += 1
            sheet.write(row, col + new_col, rec['length_of_service'], format4)
            new_col += 1

            row = row + 1
            sl_no = sl_no + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Length of Service Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.length.of.service.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_length_of_service_report_pdf(self):
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id
        # get data from sql
        data = self.employee_length_of_service_report_sql(user_work_location_id, department_id, employee_id)
        return self.env.ref('custom_hr_report.employee_length_of_service_report_tmpl').with_context(
            landscape=True).report_action(self, data=data)

    def employee_length_of_service_report_sql(self, user_work_location_id, department_id, employee_id):
        work_loc_filter = ""
        dept_filter = ""
        emp_filter = ""
        work_location_name = "All"
        dept_name = "All"
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "tbl1.emp_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "tbl1.emp_id"
        print(order_by)


        domain = []

        if user_work_location_id:
            work_loc_filter = "AND he.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if department_id:
            domain += [('department_id', '=', department_id.id)]
            dept_filter = "AND he.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if employee_id:
            domain += [('id', '=', employee_id.id)]
            emp_filter = "AND he.id = %s" % employee_id.id

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND he.sbu_unit_id = {0}".format(self.sbu_unit_id.id) 

        data_sql = """
                    SELECT tbl1.emp_id, tbl1.emp_name, tbl1.emp_id_card, tbl1.emp_joining_date, tbl1.dept_id, tbl1.des_id, tbl1.work_loc_id, tbl1.work_location_name, tbl1.department_name
                    FROM(
                        SELECT he.id AS emp_id, he.name AS emp_name, he.id_card_no AS emp_id_card, he.initial_employment_date AS emp_joining_date, he.department_id AS dept_id, he.job_id AS des_id,
                        he.user_work_location_id AS work_loc_id, sl.name as work_location_name, hd.name->>'en_US' AS department_name
                        FROM hr_employee he
                        LEFT JOIN hr_contract hc ON hc.employee_id = he.id
                        LEFT JOIN stock_location sl ON he.user_work_location_id = sl.id
                        LEFT JOIN hr_department hd on hd.id = he.department_id
                        {5} JOIN (
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {4}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = he.id
                        WHERE hc.state = 'open' AND he.active = 'true' {0} {1} {2} {3}
                        GROUP BY he.id, he.name, he.id_card_no, he.initial_employment_date, he.department_id , he.job_id, he.user_work_location_id , hc.hra,sl.name, hd.name
                        ) tbl1
                    GROUP BY tbl1.emp_id, tbl1.emp_name, tbl1.emp_id_card, tbl1.emp_joining_date, tbl1.dept_id, tbl1.des_id, tbl1.work_loc_id, tbl1.work_location_name, tbl1.department_name
                    -- ORDER BY tbl1.emp_id_card, tbl1.emp_name
                    ORDER BY {6}, tbl1.emp_name
                    """.format(work_loc_filter, dept_filter,
                                emp_filter, business_unit_filter,
                                tags_filter, tag_filter_join,
                                order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()
        data_list = []

        for d in data_res:
            length_domain = self.env['hr.employee'].search(
                [('id', '=', d['emp_id'])])
            vals = {
                'emp_id': d['emp_id'],
                'emp_name': d['emp_name'],
                'emp_joining_date': d['emp_joining_date'],
                'department_name': d['department_name'],
                'work_location_name': d['work_location_name'],
                'length_of_service': length_domain.length_of_service,
            }
            data_list.append(vals)

        data = {
            'model': "employee.length.of.service.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'work_location_name': work_location_name,
            'department_name': dept_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data
