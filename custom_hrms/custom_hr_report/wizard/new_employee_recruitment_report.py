from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from calendar import monthrange
from datetime import date
import datetime
from datetime import datetime
from itertools import groupby

import xlsxwriter

import base64
from io import BytesIO


class NewEmployeeRecruitmentReportWizard(models.TransientModel):
    _name = "new.employee.recruitment.report.wizard"
    _description = "New Employee Recruitment Report Wizard"

    def get_years(self):
        """ Get company start year and display_year from res_company """
        year_list = []
        company = self.env.company
        if company.start_date:
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

    file_data = fields.Binary('New Employee Recruitment Report Wizard')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', default=lambda self: self._get_work_loc(), domain=lambda self: self._set_domain_work_loc())
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month', required=True)

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

    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('Start date cannot be greater than the end date.'))

    def new_employee_recruitment_report_excel(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.new_employee_recruitment_report_sql(month, year, department_id, user_work_location_id)

        file_name = "New Employee Recruitment Report (%s - %s).xlsx" % (data['month'], data['year'])
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

        for line in data['csr']:
            for line2 in line:
                sheet = workbook.add_worksheet(line[line2][0]['location_name'])

                sheet.merge_range(0, 0, 0, 5, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 2, 5,
                                  "New Employee Recruitment Report (%s - %s)" % (data['month'], data['year']),
                                  format0)

                sheet.merge_range(3, 0, 3, 2, 'Work/Job Location: {0}'.format(line[line2][0]['location_name']), format1)
                sheet.merge_range(3, 3, 3, 5, 'Department Name: {0}'.format(data['dept_name']), format3)

                sheet.write(4, 0, 'Employee ID', format1)
                sheet.write(4, 1, 'Employee Name', format1)
                sheet.write(4, 2, 'Department', format1)
                sheet.write(4, 3, 'Designation', format1)
                sheet.write(4, 4, 'Joining Date', format2)
                sheet.write(4, 5, 'Gross Salary', format3)

                row = 5
                col = 0

                for line3 in line[line2]:
                    sheet.write(row, col, line3['emp_id_card'], format4)
                    sheet.write(row, col + 1, line3['employee_name'], format4)
                    sheet.write(row, col + 2, line3['dept_name'], format4)
                    sheet.write(row, col + 3, line3['designation'], format4)
                    sheet.write(row, col + 4, datetime.strptime(str(line3['joining_date']), '%Y-%m-%d').strftime('%d-%b-%Y'), format5)
                    sheet.write(row, col + 5, round(line3['gross_salary'], 2), format6)

                    row = row + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'New Employee Recruitment Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=new.employee.recruitment.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def new_employee_recruitment_report_pdf(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.new_employee_recruitment_report_sql(month, year, department_id, user_work_location_id)

        return self.env.ref(
            'custom_hr_report.new_employee_recruitment_report_tmpl').with_context(landscape=True).report_action(self, data=data)

    def new_employee_recruitment_report_sql(self, month, year, department_id, user_work_location_id):
        m = int(month)
        y = int(year)
        ndays = monthrange(y, m)[1]
        start_date = date(y, m, 1)
        end_date = date(y, m, ndays)

        dept_filter = ""
        work_loc_filter = ""
        dept_name = "All"
        work_location_name = "All"

        if department_id:
            dept_filter = "AND hr.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            work_loc_filter = "AND hr.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        data_sql = """
                    SELECT hr.name as employee_name, hr.id_card_no as emp_id_card,hj.name->>'en_US' as designation, hd.name->>'en_US' as dept_name, COALESCE(hr.user_work_location_id, 100000) AS user_work_location_id, sl.name AS location_name, hr.initial_employment_date as joining_date, hc.gross_salary as gross_salary
                    FROM hr_employee hr
                    LEFT JOIN hr_job hj ON hj.id = hr.job_id
                    LEFT JOIN hr_department hd ON hd.id = hr.department_id
                    LEFT JOIN hr_contract hc ON hc.employee_id = hr.id
                    LEFT JOIN stock_location sl ON sl.id = hr.user_work_location_id
                    WHERE DATE(hr.initial_employment_date) BETWEEN '{0}' AND '{1}' AND hc.state = 'open' {2} {3}
                    GROUP BY hr.name, hr.user_work_location_id, sl.name, hr.id_card_no, hj.name, hd.name, hr.initial_employment_date, hc.gross_salary
                    ORDER BY hr.id_card_no, hr.name, hr.user_work_location_id, sl.name,hj.name, hd.name
                    """.format(start_date, end_date, dept_filter, work_loc_filter)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        # define a fuction for key
        def key_func(k):
            return k['user_work_location_id']

        data_res = sorted(data_res, key=key_func)

        final_data_list = []

        for key, value in groupby(data_res, key_func):
            vals = {
                key: list(value)
            }
            final_data_list.append(vals)

        data = {
            'model': "new.employee.recruitment.report.wizard",
            'form': self.read()[0],
            'csr': final_data_list,
            'month': dict(self._fields['month'].selection).get(self.month),
            'year': year,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
        }
        return data