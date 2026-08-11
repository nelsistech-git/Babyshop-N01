from odoo import fields, models, api
from calendar import monthrange
from datetime import date
import datetime
import copy
from itertools import groupby
from datetime import datetime
import xlsxwriter

import base64
from io import BytesIO


class EmployeeLeaveEncashmentReportWizard(models.TransientModel):
    _name = "employee.leave.encashment.report.wizard"
    _description = "Employee Leave Encashment Report"

    def get_years(self):
        """ Get company start year and display_year from res_company """
        year_list = []
        company = self.env.company
        if company.start_date:
            # start_year = int(str(company.start_date).split("-")[0])
            start_year = company.start_date.year
            if company.display_year:
                display_years = company.display_year
                for i in range(start_year, start_year + display_years, 1):
                    list_format = '%s' % i, i
                    year_list.append(list_format)
        else:
            if company.display_year:
                start_year = datetime.today().year
                display_years = company.display_year
                for i in range(start_year, start_year + display_years, 1):
                    list_format = '%s' % i, i
                    year_list.append(list_format)
            else:
                list_format = '%s' % datetime.today().year, datetime.today().year
                year_list.append(list_format)
        return year_list

    file_data = fields.Binary('Employee Leave Encashment Report')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       default=lambda self: self._get_work_loc(),
                                       domain=lambda self: self._set_domain_work_loc())
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')

    category_ids = fields.Many2many('hr.employee.category', 'employee_leave_encashment_employee_category_rel', 
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

    def employee_leave_encashment_report_excel(self):
        year = self.year
        company_id = self.company_id
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        # get data from sql
        data = self.employee_leave_encashment_report_sql(year, user_work_location_id, department_id, employee_id)

        file_name = "Employee Leave Encashment Report.xlsx"
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

        for line in data['csr']:
            for line2 in line:
                sheet = workbook.add_worksheet(line[line2][0]['loc_name'])

                sheet.merge_range(8, 0, 5, 0, 'Sl. No.', format1)
                sheet.merge_range(8, 1, 5, 1, 'Employee Name', format1)
                sheet.merge_range(8, 2, 5, 2, 'Employee ID', format1)
                sheet.merge_range(8, 3, 5, 3, 'Work/Job Location', format1)
                sheet.merge_range(8, 4, 5, 4, 'Department', format2)
                sheet.merge_range(8, 5, 5, 5, 'Designation', format2)
                sheet.merge_range(8, 6, 5, 6, 'Gross Salary', format2)

                leave_type_list = data['leave_type_list']
                head_col = 7

                for l in range(len(leave_type_list)):
                    sheet.merge_range(8, head_col, 5, head_col+2, leave_type_list[l]['leave_name'], format2)

                    head_col = head_col + 3

                sheet.merge_range(8, head_col, 5, head_col+2, 'Total', format2)
                sheet.merge_range(8, head_col+3, 5, head_col+3, 'Per Day salary', format2)
                sheet.merge_range(8, head_col+4, 5, head_col+4, 'Leave Encashment', format2)
                sheet.merge_range(0, 0, 0, head_col+4, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 2, head_col+4,
                                  "Employee Leave Encashment Report",
                                  format0)
                sheet.merge_range(3, 0, 3, int((head_col+2)/2), 'Work/Job Location: {0}'.format(data['work_location_name']), format1)
                sheet.merge_range(3, int((head_col+2)/2) + 1, 3, head_col+4, 'Department Name: {0}'.format(data['dept_name']), format3)

                sheet.merge_range(4, 0, 4, int((head_col+2)/2), 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
                sheet.merge_range(4, 7, 4, head_col+4, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format3)

                head_col2 = 6

                for i in range(len(leave_type_list) + 1):
                    sheet.write(5, head_col2, 'Allocation', format2)
                    sheet.write(5, head_col2+1, 'Enjoy', format2)
                    sheet.write(5, head_col2+2, 'Remain', format2)
                    sheet.write(5, head_col2+3, 'Per Day Salary', format2)

                    head_col2 = head_col2 + 3

                row = 6
                col = 0
                type_col = 7

                sl_no = 1
                total_alloc_count = 0
                total_leave_count = 0
                total_remain = 0

                for line3 in line[line2]:
                    sheet.write(row, col, sl_no, format5)
                    sheet.write(row, col + 1, line3['emp_name'], format4)
                    sheet.write(row, col + 2, line3['old_emp_id'], format4)
                    sheet.write(row, col + 3, line3['loc_name'], format4)
                    sheet.write(row, col + 4, line3['dept_name'], format4)
                    sheet.write(row, col + 5, line3['job_name'], format4)
                    sheet.write(row, col + 6, line3['gross_salary'], format4)

                    for j in line3['leave_types']:

                        sheet.write(row, type_col, j['alloc_count'], format5)
                        total_alloc_count = total_alloc_count + j['alloc_count']
                        sheet.write(row, type_col + 1, j['leave_count'], format5)
                        total_leave_count = total_leave_count + j['leave_count']
                        sheet.write(row, type_col + 2, j['leave_remain'], format5)
                        total_remain = total_remain + j['leave_remain']

                        type_col = type_col + 3

                    sheet.write(row, type_col, total_alloc_count, format5)
                    sheet.write(row, type_col + 1, total_leave_count, format5)
                    sheet.write(row, type_col + 2, total_remain, format5)
                    sheet.write(row, type_col + 3, '{0:,.2f}'.format(line3['per_day_salary']), format4)
                    sheet.write(row, type_col + 4, '{0:,.2f}'.format(line3['per_day_salary'] * total_remain), format4)

                    row = row + 1
                    sl_no = sl_no + 1
                    type_col = 6

                    total_alloc_count = 0
                    total_leave_count = 0
                    total_remain = 0

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Leave Encashment Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.leave.encashment.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_leave_encashment_report_pdf(self):
        year = self.year
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        data = self.employee_leave_encashment_report_sql(year, user_work_location_id, department_id, employee_id)
        return self.env.ref('custom_hr_report.employee_leave_encashment_report_tmpl').with_context(
            landscape=True).report_action(self, data=data)

    def employee_leave_encashment_report_sql(self, year, user_work_location_id, department_id, employee_id):
        year = int(year)
        work_loc_filter = ""
        dept_filter = ""
        emp_filter = ""
        work_location_name = "All"
        dept_name = "All"
        filter = ""
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "emp_tbl.em_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "emp_tbl.old_emp_id"
        print(order_by)

        if user_work_location_id:
            work_loc_filter = "AND emp_tbl.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if department_id:
            dept_filter = "AND hd.id = %s" % department_id.id
            dept_name = department_id.display_name

        if employee_id:
            emp_filter = "AND emp_tbl.emp_id = %s" % employee_id.id

        if any([user_work_location_id, department_id, employee_id]):
            filter = "WHERE" + work_loc_filter + dept_filter + emp_filter
            filter = filter.replace('AND', '', 1)

        leave_type_obj = self.env['hr.leave.type'].search([('year', '=', str(year)),('is_allow_leave_encashment', '=', True)], order="sequence ASC")

        leave_type_list = []

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "WHERE hre.sbu_unit_id = {0}".format(self.sbu_unit_id.id) 


        # leave types list
        for rec in leave_type_obj:
            leave_name = rec.display_name
            leave_seq = str(rec.sequence)
            alloc_count = 0
            leave_count = 0
            leave_remain = 0
            vals = {
                'leave_seq': leave_seq,
                'leave_name': leave_name,
                'alloc_count': alloc_count,
                'leave_count': leave_count,
                'leave_remain': leave_remain
            }
            leave_type_list.append(vals)
        # master sql - employee info
        data_sql = """
                        SELECT emp_tbl.emp_id AS emp_id, stl.name AS loc_name, COALESCE(emp_tbl.user_work_location_id, 100000) AS user_work_location_id, 
                        emp_tbl.old_emp_id AS old_emp_id, emp_tbl.em_name AS emp_name, hd.name->>'en_US' AS dept_name,hj.name->>'en_US' AS job_name, emp_tbl.gross_salary
                        FROM (
                            SELECT hre.id AS emp_id, hre.user_work_location_id AS user_work_location_id, hre.name AS emp_name, hre.id_card_no AS old_emp_id, 
                                hre.name AS em_name, hre.department_id AS dept_id, hre.job_id AS job_id, hc.att_policy_id, hc.gross_salary as gross_salary,
                            COALESCE(SUM(CASE WHEN easl.status in ('ab', 'leave') OR easl.status IS NULL THEN 1 ELSE 0 END), 0) AS no_of_days,
                            COALESCE(SUM(CASE WHEN easl.status in ('ab', 'leave', 'weekend', 'ph') OR easl.status IS NULL THEN 1 ELSE 0 END), 0) AS no_of_days_w
                            FROM hr_employee hre
                            LEFT JOIN hr_contract hc ON hc.employee_id = hre.id
                            JOIN employee_attendance_sheet_line easl ON easl.employee_id = hre.id
                            JOIN (SELECT DISTINCT(employee_id) AS employee_id FROM hr_leave_allocation
                            WHERE state='validate') alo ON hre.id = alo.employee_id
                            {3} JOIN (
                                    SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                    JOIN hr_employee_category etag on etag.id=ecr.category_id
                                    {2}
                                    GROUP BY emp_id
                                ) emp_tag ON emp_tag.emp_id = hre.id
                            {1}
                            GROUP BY hre.id, hc.att_policy_id, hc.gross_salary
                        ) emp_tbl
                        LEFT JOIN hr_department AS hd on hd.id = emp_tbl.dept_id
                        LEFT JOIN hr_job hj ON hj.id = emp_tbl.job_id
                        LEFT JOIN stock_location stl ON stl.id = emp_tbl.user_work_location_id
                        LEFT JOIN attendance_sheet ah on ah.employee_id = emp_tbl.emp_id
                        GROUP BY emp_tbl.emp_id, stl.name,emp_tbl.user_work_location_id,emp_tbl.old_emp_id,emp_tbl.em_name, hd.name,hj.name,emp_tbl.gross_salary
                        --  ORDER BY emp_tbl.old_emp_id, emp_tbl.emp_id
                        ORDER BY {4}, emp_tbl.emp_id
                        """.format(filter, business_unit_filter,
                                    tags_filter, tag_filter_join,
                                    order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        # leave info sql - allocate, leave
        leave_sql = """
        SELECT tbl1.emp_id, tbl1.sequence, COALESCE(tbl1.alloc_count, 0) AS alloc_count, COALESCE(tbl2.leave_count, 0) AS leave_count, tbl1.leave_encashment
                        FROM(
                            SELECT hlt.sequence AS sequence, hla.employee_id AS emp_id, hla.number_of_days AS alloc_count, hlt.is_allow_leave_encashment as leave_encashment
                            FROM hr_leave_type hlt
                            LEFT JOIN hr_leave_allocation hla ON hla.holiday_status_id = hlt.id
                            WHERE hla.state='validate' AND hlt.active='True' AND hlt.year = '{0}'
                            GROUP BY hlt.id, hlt.sequence, hla.id, hla.number_of_days, hlt.is_allow_leave_encashment
                            ORDER BY hlt.sequence
                            ) tbl1
                        LEFT JOIN (
                            SELECT leave_tbl.sequence, leave_tbl.emp_id, COALESCE(SUM(hld.leave_no), 0) AS leave_count
                            FROM (
                                    SELECT hl.id AS leave_id, hlt.sequence AS sequence, hl.employee_id AS emp_id
                                    FROM hr_leave hl
                                    LEFT JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                                    WHERE hl.state='validate' AND hlt.is_allow_leave_encashment = 'True'
                                    GROUP BY hl.id, hlt.sequence, hl.employee_id
                                ) leave_tbl
                            LEFT JOIN hr_leave_details hld ON hld.leave_id = leave_tbl.leave_id
                            GROUP BY leave_tbl.sequence, leave_tbl.emp_id
                            ORDER BY leave_tbl.sequence
                            ) tbl2 ON (tbl2.emp_id = tbl1.emp_id AND tbl2.sequence = tbl1.sequence)
                        ORDER BY tbl1.emp_id, tbl1.sequence""".format(year)
        self.env.cr.execute(leave_sql)
        leave_res = self.env.cr.dictfetchall()
        # --------------------
        data_list = []

        sum_of_leave_encashment = 0
        for rec in data_res:
            attendance_sheet_obj = self.env['attendance.sheet'].search([('employee_id', '=', rec['emp_id'])], order='id desc', limit=1)
            if attendance_sheet_obj.per_day_salary:
                sum_count = attendance_sheet_obj.per_day_salary
                sum_of_leave_encashment += sum_count
            else:
                sum_count = 0
                sum_of_leave_encashment += sum_count

            vals = {
                'emp_id': rec['emp_id'],
                'emp_name': rec['emp_name'],
                'old_emp_id': rec['old_emp_id'],
                'loc_name': rec['loc_name'],
                'user_work_location_id': rec['user_work_location_id'],
                'dept_name': rec['dept_name'],
                'job_name': rec['job_name'],
                'gross_salary': rec['gross_salary'],
                'per_day_salary': sum_count,
                'total_of_leave_encashment': sum_of_leave_encashment,
                'leave_types': copy.deepcopy(leave_type_list)
            }

            data_list.append(vals)
        # updating leave info
        for rec in data_list:  # master data loop
                emp_id = rec['emp_id']
                leave_types_list = rec['leave_types']
                for rec2 in leave_res:  # leave data loop
                    leave_emp_id = rec2['emp_id']
                    leave_seq = str(rec2['sequence'])
                    leave_alloc_count = rec2['alloc_count']
                    leave_leave_count = rec2['leave_count']
                    leave_remain_count = 0
                    per_day_salary_value = rec['per_day_salary']
                    # checking whether leave employee id and master data employee id matches
                    if leave_emp_id == emp_id:
                        if year:
                            for j in range(len(leave_types_list)):  # leave type list loop
                                type_dict = leave_types_list[j]
                                # checking whether leave type list sequence and leave sequence from leave sql matches

                                if type_dict['leave_seq'] == leave_seq:
                                    type_dict['alloc_count'] = leave_alloc_count
                                    type_dict['leave_count'] = leave_leave_count
                                    type_dict['leave_remain'] = leave_alloc_count - leave_leave_count
                                    leave_remain_count = type_dict['leave_remain']
                                    break
        # define a fuction for key
        def key_func(k):
            return k['user_work_location_id']

        data_list = sorted(data_list, key=key_func)

        final_data_list = []

        for key, value in groupby(data_list, key_func):
            vals = {
                key: list(value)
            }
            final_data_list.append(vals)

        data = {
            'model': "employee.leave.encashment.report.wizard",
            'form': self.read()[0],
            'csr': final_data_list,
            'leave_type_list': leave_type_list,
            'leave_type_list_len': (len(leave_type_list) * 3) + 6,
            'year': year,
            'work_location_name': work_location_name,
            'dept_name': dept_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data