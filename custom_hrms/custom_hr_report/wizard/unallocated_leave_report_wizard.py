from odoo import fields, models, api, _, exceptions
from odoo.exceptions import ValidationError
from calendar import monthrange
import datetime
from datetime import datetime, date, timedelta
import copy
import pytz

import xlsxwriter

import base64
from io import BytesIO


def get_years():
    year_list = []
    crn_year = datetime.now().year
    for i in range(2022, crn_year + 5):
        year_list.append((str(i), str(i)))
    return year_list


class UnallocatedEmployeeLeaveReportWizard(models.TransientModel):
    _name = "unallocated.employee.leave.report.wizard"
    _description = "Unallocated Employee Leave Report Wizard"

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

    file_data = fields.Binary('Unallocated Employee Leave Report')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    leave_type_id = fields.Many2one('hr.leave.type', string='Leave Type',
                                    domain="[('type_code', '!=', False), ('year', '=', year)]")

    def _set_domain_work_loc(self):
        if self.env.user.user_work_location_id:
            return [('is_work_loc', '=', True), ('state', '=', 'done'), ('id', '=', self.env.user.user_work_location_id.id)]
        else:
            return [('is_work_loc', '=', True), ('state', '=', 'done')]

    @api.model
    def _get_work_loc(self):
        if self.env.user.user_work_location_id:
            return self.env.user.user_work_location_id.id

    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       default=lambda self: self._get_work_loc(),
                                       domain=lambda self: self._set_domain_work_loc())

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

    def unallocated_employee_leave_report_pdf(self):
        year = self.year
        work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id
        leave_type_id = self.leave_type_id

        # get data from sql
        data = self.unallocated_employee_leave_report_sql(year, work_location_id, department_id, employee_id,
                                                          leave_type_id)

        return self.env.ref(
            'custom_hr_report.unallocated_leave_report_tmpl').with_context(
            landscape=False).report_action(self, data=data)

    def unallocated_employee_leave_report_excel(self):
        year = self.year
        work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id
        leave_type_id = self.leave_type_id

        # get data from sql
        data = self.unallocated_employee_leave_report_sql(year, work_location_id, department_id, employee_id,
                                                          leave_type_id)

        file_name = "Unallocated Employee Leave Report (%s - %s).xlsx"
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

        sheet = workbook.add_worksheet('Unallocated Employee Leave Report')

        sheet.merge_range(0, 0, 0, 5, "{0}".format(data['form']['company_id'][1]), format0)
        sheet.merge_range(1, 0, 2, 5, "Unallocated Employee Leave Report", format0)
        sheet.merge_range(3, 0, 3, 2, 'Year: {0}'.format(data['form']['year']), format1)
        sheet.merge_range(4, 0, 4, 2, 'Leave Type: {0}'.format(data['leave_type_name']), format1)
        sheet.merge_range(3, 3, 3, 5, 'Work/Job Location: {0}'.format(data['work_loc_name']), format1)
        sheet.merge_range(4, 3, 4, 5, 'Department Name: {0}'.format(data['dept_name']), format1)
        sheet.merge_range(5, 3, 5, 5, 'Employee: {0}'.format(data['employee_name']), format1)
        sheet.merge_range(5, 0, 5, 2, None, format1)

        sheet.write(6, 0, 'Employee ID', format2)
        sheet.write(6, 1, 'Employee Name', format1)
        sheet.write(6, 2, 'Joining Date', format2)
        sheet.write(6, 3, 'Work/Job Location', format1)
        sheet.write(6, 4, 'Department', format1)
        sheet.write(6, 5, 'Designation', format1)

        row = 6
        col = 0

        for rec in data['csr']:
            sheet.write(row, col + 0, rec['emp_id_card'], format5)
            sheet.write(row, col + 1, rec['employee_name'], format4)
            joining_date = datetime.strptime(str(rec['joining_date']), '%Y-%m-%d').strftime('%d-%b-%Y') if rec[
                'joining_date'] else None
            sheet.write(row, col + 2, joining_date, format5)
            sheet.write(row, col + 3, rec['location_name'], format4)
            sheet.write(row, col + 4, rec['dept_name'], format4)
            sheet.write(row, col + 5, rec['job_name'], format4)

            row = row + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Unallocated Employee Leave Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=unallocated.employee.leave.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def unallocated_employee_leave_report_sql(self, year, work_location_id, department_id, employee_id, leave_type_id):
        work_loc_filter = ""
        dept_filter = ""
        emp_filter = ""
        leave_type_filter = ""

        work_location_name = "All"
        dept_name = "All"
        employee_name = "All"
        leave_type_name = "All"

        if work_location_id:
            work_loc_filter = "AND he.user_work_location_id = %s" % work_location_id.id
            work_location_name = work_location_id.display_name

        if department_id:
            dept_filter = "AND he.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if employee_id:
            emp_filter = "AND he.id = %s" % employee_id.id
            employee_name = employee_id.display_name

        if leave_type_id:
            leave_type_filter = "AND hla.holiday_status_id = %s" % leave_type_id.id
            leave_type_name = leave_type_id.display_name

        data_sql = """
                    SELECT he.id AS emp_id, he.name AS emp_name, he.id_card_no AS emp_id_card, he.initial_employment_date AS emp_joining_date, sl.name AS work_location_name, hd.name->>'en_US' AS dept_name,hj.name->>'en_US' AS desig_name
                    FROM hr_employee he
                    LEFT JOIN hr_contract hc ON hc.employee_id = he.id
                    LEFT JOIN stock_location sl ON he.user_work_location_id = sl.id
                    LEFT JOIN hr_department hd on hd.id = he.department_id
                    LEFT JOIN hr_job hj ON hj.id = he.job_id
                    WHERE hc.state = 'open' AND he.active = 'true' AND he.id NOT IN (
                        SELECT DISTINCT(hla.employee_id) FROM hr_leave_allocation hla
                        LEFT JOIN hr_leave_type hlt ON hlt.id = hla.holiday_status_id
                        WHERE hla.employee_id IS NOT NULL AND hla.state = 'validate' AND hlt.year = '{0}' {1}
                        ORDER BY hla.employee_id
                    ) {2} {3} {4}
                    GROUP BY he.id, he.name, he.id_card_no, he.initial_employment_date, sl.name, hd.name, hj.name
                    ORDER BY he.id_card_no, he.id
                    """.format(year, leave_type_filter, work_loc_filter, dept_filter, emp_filter)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        data = {
            'model': 'unallocated.employee.leave.report.wizard',
            'form': self.read()[0],
            'csr': data_res,
            'employee_name': employee_name,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'leave_type_name': leave_type_name
        }
        return data
