from datetime import date
from calendar import monthrange
import datetime
from odoo import fields, models, api, _
from itertools import groupby
import xlsxwriter

import base64
from io import BytesIO


class EmployeeResignReportWizard(models.TransientModel):
    _name = "employee.resign.report.wizard"
    _description = "Employee Resign Report Wizard"

    file_data = fields.Binary('Employee Resign Report')
    year = fields.Selection(
        [(str(yearno), str(yearno)) for yearno in range(2021, ((datetime.date.today().year) + 5))],
        default=str(datetime.date.today().year), string='Year', required=True)

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

    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', default=lambda self: self._get_work_loc(), domain=lambda self: self._set_domain_work_loc())
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    category_ids = fields.Many2many('hr.employee.category', 'employee_resign_employee_category_rel', 
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

    def employee_resign_report_excel(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.employee_resign_report_sql(year, month, department_id, user_work_location_id)

        file_name = "Employee Resign Report (%s - %s).xlsx" % (data['month'], data['year'])
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
                sheet = workbook.add_worksheet(line[line2][0]['location_name'])

                sheet.merge_range(0, 0, 0, 6, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 2, 6,
                                  "Employee Resign Report (%s - %s)" % (data['month'], data['year']),
                                  format0)

                sheet.merge_range(3, 0, 3, 1, 'Work/Job Location: {0}'.format(line[line2][0]['location_name']), format1)
                sheet.merge_range(3, 2, 3, 3, 'Department Name: {0}'.format(data['dept_name']), format1)
                sheet.merge_range(3, 4, 3, 5, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
                sheet.write(3, 6, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: None Selected", format1)


                sheet.write(4, 0, 'Employee ID No.', format2)
                sheet.write(4, 1, 'Name of Employee', format1)
                sheet.write(4, 2, 'Work/Job Location', format1)
                sheet.write(4, 3, 'Department', format1)
                sheet.write(4, 4, 'Designation', format1)
                sheet.write(4, 5, 'Resign Date', format2)
                sheet.write(4, 6, 'Gross Salary', format3)

                row = 5
                col = 0

                for line3 in line[line2]:
                    new_col = 0
                    sheet.write(row, col, line3['id_card_no'], format5)
                    new_col += 1
                    sheet.write(row, col + new_col, line3['emp_name'], format4)
                    new_col += 1
                    sheet.write(row, col + new_col, line3['location_name'], format4)
                    new_col += 1
                    sheet.write(row, col + new_col, line3['dept_name'], format4)
                    new_col += 1
                    sheet.write(row, col + new_col, line3['designation_name'], format4)
                    new_col += 1
                    sheet.write(row, col + new_col, datetime.datetime.strptime(str(line3['resign_date']), '%Y-%m-%d').strftime('%d-%b-%Y'), format5)
                    new_col += 1
                    sheet.write(row, col + new_col, round(line3['gross_salary'], 2), format6)
                    new_col += 1

                    row = row + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Resign Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.resign.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_resign_report_pdf(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.employee_resign_report_sql(year, month, department_id, user_work_location_id)

        return self.env.ref('custom_hr_report.employee_resign_report_id').with_context(
            landscape=False).report_action(self, data=data)

    def employee_resign_report_sql(self, year, month, department_id, user_work_location_id):
        m = int(month)
        y = int(year)
        ndays = monthrange(y, m)[1]
        from_date = date(y, m, 1)
        to_date = date(y, m, ndays)


        dept_filter = ""
        work_loc_filter = ""
        dept_name = "All"
        work_location_name = "All"
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "tbl1.emp_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "tbl1.id_card_no"
        print(order_by)

        if department_id:
            dept_filter = "AND hre.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            work_loc_filter = "AND hre.user_work_location_id = %s" % user_work_location_id.id
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
                    SELECT tbl1.emp_name, sl.name AS location_name, tbl1.user_work_location_id, tbl1.id_card_no, hj.name->>'en_US' AS designation_name, hd.name->>'en_US' AS dept_name,
                    hreg.expected_revealing_date AS resign_date, tbl1.gross_salary
                    FROM(
                        SELECT hre.id AS emp_id, hre.name AS emp_name, hre.user_work_location_id, hre.id_card_no, hre.job_id, hre.department_id, hc.gross_salary
                        FROM hr_employee hre
                        JOIN hr_contract hc ON hc.employee_id = hre.id
                        {6} JOIN (
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {5}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = hre.id
                        WHERE hc.state='open' {2} {3} {4}
                        ORDER BY emp_name
                    ) tbl1
                    LEFT JOIN hr_resignation hreg ON hreg.employee_id=tbl1.emp_id
                    LEFT JOIN hr_job hj ON hj.id = tbl1.job_id
                    LEFT JOIN hr_department hd ON hd.id = tbl1.department_id
                    LEFT JOIN stock_location sl ON sl.id = tbl1.user_work_location_id
                    WHERE hreg.state='approved' AND hreg.expected_revealing_date BETWEEN '{0}' AND '{1}'
                    -- ORDER BY tbl1.id_card_no, tbl1.emp_name
                    ORDER BY {7}, tbl1.emp_name
                    """.format(from_date, to_date, dept_filter, work_loc_filter,
                               business_unit_filter, tags_filter, tag_filter_join, order_by)

        self.env.cr.execute(data_sql)
        data_list = self.env.cr.dictfetchall()

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
            'model': "employee.resign.report.wizard",
            'form': self.read()[0],
            'csr': final_data_list,
            'year': year,
            'month': dict(self._fields['month'].selection).get(month),
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data