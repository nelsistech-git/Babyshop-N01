from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from calendar import monthrange
from datetime import date
import datetime
from datetime import datetime
import xlsxwriter

import base64
from io import BytesIO


class EmployeeMigrationReportWizard(models.TransientModel):
    _name = "employee.migration.report.wizard"
    _description = "Employee Migration Report Wizard"

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

    file_data = fields.Binary('Employee Migration Report Wizard')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    transfer_company = fields.Selection([
        ('0', 'Same Company'),
        ('1', 'Other Company')
    ], string="Transfer Type", default='0')
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

    def employee_migration_report_pdf(self):
        year = self.year
        month = self.month
        transfer_company = self.transfer_company
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.employee_migration_report_sql(month, year, transfer_company,  department_id, user_work_location_id)

        return self.env.ref(
            'custom_hr_report.employee_migration_report_tmpl').with_context(landscape=True).report_action(self, data=data)

    def employee_migration_report_excel(self):
        year = self.year
        month = self.month
        transfer_company = self.transfer_company
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.employee_migration_report_sql(month, year, transfer_company,  department_id, user_work_location_id)

        file_name = "Employee Migration Report (%s - %s).xlsx" % (data['month'], data['year'])
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

        sheet = workbook.add_worksheet('Employee Migration Report')

        if data['transfer_company'] == 'all':
            sheet.merge_range(0, 0, 0, 18, "{0}".format(data['form']['company_id'][1]), format0)
            sheet.merge_range(1, 0, 2, 18,
                              "Employee Migration Report (%s - %s)" % (data['month'], data['year']),
                              format0)

            sheet.merge_range(3, 0, 3, 6, 'Work/Job Location: {0}'.format(data['work_loc_name']), format1)
            sheet.merge_range(3, 7, 3, 12, 'Transfer Type: All', format2)
            sheet.merge_range(3, 13, 3, 18, 'Department Name: {0}'.format(data['dept_name']), format3)


            sheet.merge_range(4, 0, 5, 0, 'Sl.', format2)
            sheet.merge_range(4, 1, 5, 1, 'Type', format1)
            sheet.merge_range(4, 2, 5, 2, 'Employee ID No', format1)
            sheet.merge_range(4, 3, 5, 3, 'Employee Name', format1)
            sheet.merge_range(4, 4, 4, 7, 'Previous Allocation', format2)
            sheet.write(5, 4, 'Previous Job/Work Location', format1)
            sheet.write(5, 5, 'Previous Department', format1)
            sheet.write(5, 6, 'Previous Designation', format1)
            sheet.write(5, 7, 'Previous Reporting Manager', format1)
            sheet.merge_range(4, 8, 4, 11, 'Same Company Transfer', format2)
            sheet.write(5, 8, 'Revised Job/Work Location', format1)
            sheet.write(5, 9, 'Revised Department', format1)
            sheet.write(5, 10, 'Revised Designation', format1)
            sheet.write(5, 11, 'Revised Reporting Manager', format1)
            sheet.merge_range(4, 12, 4, 17, 'Other Company Transfer', format2)
            sheet.write(5, 12, 'Previous Company Name', format1)
            sheet.write(5, 13, 'Revised Company Name', format1)
            sheet.write(5, 14, 'Revised Job/Work Location', format1)
            sheet.write(5, 15, 'Revised Department', format1)
            sheet.write(5, 16, 'Revised Designation', format1)
            sheet.write(5, 17, 'Revised Reporting Manager', format1)
            sheet.merge_range(4, 18, 5, 18, 'Remarks', format2)

            row = 6
            col = 0

            sl_no = 1

            for rec in data['csr']:
                sheet.write(row, col, sl_no, format5)
                sheet.write(row, col + 1, rec['id_card_no'], format4)
                sheet.write(row, col + 2, rec['employee_name'], format4)
                sheet.write(row, col + 3, rec['from_loc_name'], format4)
                sheet.write(row, col + 4, rec['from_dept_name'], format4)
                sheet.write(row, col + 5, rec['from_job_pos_name'], format4)
                sheet.write(row, col + 6, rec['from_manager_name'], format4)
                sheet.write(row, col + 7, rec['to_loc_name'], format4)
                sheet.write(row, col + 8, rec['to_dept_name'], format4)
                sheet.write(row, col + 9, rec['to_job_pos_name'], format4)
                sheet.write(row, col + 10, rec['to_manager_name'], format4)
                sheet.write(row, col + 11, rec['company_name'], format4)
                sheet.write(row, col + 12, rec['other_company_name'], format4)
                sheet.write(row, col + 13, rec['other_company_job_location'], format4)
                sheet.write(row, col + 14, rec['other_company_dept_name'], format4)
                sheet.write(row, col + 15, rec['other_company_job_position'], format4)
                sheet.write(row, col + 16, rec['other_company_manager_name'], format4)
                sheet.write(row, col + 17, rec['note'], format4)
                sheet.write(row, col + 18, None, format5)


                row = row + 1
                sl_no = sl_no + 1

        elif data['transfer_company'] == '0':
            sheet.merge_range(0, 0, 0, 11, "{0}".format(data['form']['company_id'][1]), format0)
            sheet.merge_range(1, 0, 2, 11,
                              "Employee Migration Report (%s - %s)" % (data['month'], data['year']),
                              format0)

            sheet.merge_range(3, 0, 3, 3, 'Work/Job Location: {0}'.format(data['work_loc_name']), format1)
            sheet.merge_range(3, 4, 3, 7, 'Transfer Type: Same Company', format2)
            sheet.merge_range(3, 8, 3, 11, 'Department Name: {0}'.format(data['dept_name']), format3)

            sheet.write(4, 0, 'Sl.', format2)
            sheet.write(4, 1, 'Employee Name', format1)
            sheet.write(4, 2, 'Employee ID No', format1)
            sheet.write(4, 3, 'Previous Job/Work Location', format1)
            sheet.write(4, 4, 'Previous Department', format1)
            sheet.write(4, 5, 'Previous Designation', format1)
            sheet.write(4, 6, 'Previous Reporting Manager', format1)
            sheet.write(4, 7, 'Revised Job/Work Location', format1)
            sheet.write(4, 8, 'Revised Department', format1)
            sheet.write(4, 9, 'Revised Designation', format1)
            sheet.write(4, 10, 'Revised Reporting Manager', format1)
            sheet.write(4, 11, 'Remarks', format1)


            row = 5
            col = 0

            sl_no = 1

            for rec in data['csr']:
                sheet.write(row, col, sl_no, format5)
                sheet.write(row, col + 1, rec['employee_name'], format4)
                sheet.write(row, col + 2, rec['id_card_no'], format4)
                sheet.write(row, col + 3, rec['from_loc_name'], format4)
                sheet.write(row, col + 4, rec['from_dept_name'], format4)
                sheet.write(row, col + 5, rec['from_job_pos_name'], format4)
                sheet.write(row, col + 6, rec['from_manager_name'], format4)
                sheet.write(row, col + 7, rec['to_loc_name'], format4)
                sheet.write(row, col + 8, rec['to_dept_name'], format4)
                sheet.write(row, col + 9, rec['to_job_pos_name'], format4)
                sheet.write(row, col + 10, rec['to_manager_name'], format4)
                sheet.write(row, col + 11, rec['note'], format4)


                row = row + 1
                sl_no = sl_no + 1


        else:
            sheet.merge_range(0, 0, 0, 14, "{0}".format(data['form']['company_id'][1]), format0)
            sheet.merge_range(1, 0, 2, 14,
                              "Employee Migration Report (%s - %s)" % (data['month'], data['year']),
                              format0)

            sheet.merge_range(3, 0, 3, 4, 'Work/Job Location: {0}'.format(data['work_loc_name']), format1)
            sheet.merge_range(3, 5, 3, 9, 'Transfer Type: Other Company', format2)
            sheet.merge_range(3, 10, 3, 14, 'Department Name: {0}'.format(data['dept_name']), format3)

            sheet.write(4, 0, 'Sl.', format2)
            sheet.write(4, 1, 'Employee Name', format1)
            sheet.write(4, 2, 'Employee ID No', format1)
            sheet.write(4, 3, 'Previous Company Name', format1)
            sheet.write(4, 4, 'Previous Job/Work Location', format1)
            sheet.write(4, 5, 'Previous Department', format1)
            sheet.write(4, 6, 'Previous Designation', format1)
            sheet.write(4, 7, 'Previous Reporting Manager', format1)
            sheet.write(4, 8, 'Revised Reporting Manager', format1)
            sheet.write(4, 9, 'Revised Company Name', format1)
            sheet.write(4, 10, 'Revised Job/Work Location', format1)
            sheet.write(4, 11, 'Revised Department', format1)
            sheet.write(4, 12, 'Revised Designation', format1)
            sheet.write(4, 13, 'Revised Reporting Manager', format1)
            sheet.write(4, 14, 'Remarks', format1)

            row = 5
            col = 0

            sl_no = 1

            for rec in data['csr']:
                sheet.write(row, col + 0, sl_no, format5)
                sheet.write(row, col + 1, rec['employee_name'], format4)
                sheet.write(row, col + 2, rec['id_card_no'], format4)
                sheet.write(row, col + 3, rec['from_loc_name'], format4)
                sheet.write(row, col + 4, rec['from_dept_name'], format4)
                sheet.write(row, col + 5, rec['from_job_pos_name'], format4)
                sheet.write(row, col + 6, rec['from_manager_name'], format4)
                sheet.write(row, col + 7, rec['company_name'], format4)
                sheet.write(row, col + 8, rec['other_company_name'], format4)
                sheet.write(row, col + 9, rec['other_company_job_location'], format4)
                sheet.write(row, col + 10, rec['other_company_dept_name'], format4)
                sheet.write(row, col + 11, rec['other_company_job_position'], format4)
                sheet.write(row, col + 12, rec['other_company_manager_name'], format4)
                sheet.write(row, col + 13, rec['note'], format4)
                sheet.write(row, col + 14, None, format5)


                row = row + 1
                sl_no = sl_no + 1


        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Migration Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.migration.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_migration_report_sql(self, month, year, transfer_company, department_id, user_work_location_id):
        m = int(month)
        y = int(year)
        ndays = monthrange(y, m)[1]
        start_date = date(y, m, 1)
        end_date = date(y, m, ndays)

        transfer_company_val = 'all'
        transfer_company_filter = ""

        if transfer_company:
            transfer_company_val = transfer_company
            transfer_company_filter ="AND transfer_company = '%s'" % transfer_company

        dept_filter = ""
        work_loc_filter = ""
        dept_name = "All"
        work_location_name = "All"

        if department_id:
            dept_filter = "AND department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            work_loc_filter = "AND location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        data_sql = """
                    SELECT transfer_company AS t_type, employee_id AS emp_id, company_id AS company_name, id_card_no AS id_card_no, location_id AS from_loc_id, to_wh_location_id AS to_loc_id, department_id AS from_dept_id,
                    to_department_id AS to_dept_id, 
                    job_position AS from_job_pos, to_position AS to_job_pos, manager_id AS from_manager_id, to_manager_id AS to_manager_id,
                    other_company_name AS other_comp_name, other_company_job_location AS other_comp_job_loc, other_company_department AS other_comp_dept, 
                    other_company_job_position AS other_comp_job_pos,
                    other_company_manager AS other_comp_manager, note AS remarks
                    FROM hr_transfer
                    WHERE state='transfer' AND DATE(date_exec) BETWEEN '{0}' AND '{1}' {2} {3} {4}
                    ORDER BY id_card_no
                    """.format(start_date, end_date, transfer_company_filter, dept_filter, work_loc_filter)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()
        data_list = []

        for d in data_res:
            emp_id = self.env['hr.employee'].browse(d['emp_id'])
            vals = {
                'employee_name': emp_id.name,
                'id_card_no': d['id_card_no'],
                'transfer_type': d['t_type'],
                'company_name': self.env['res.company'].search([('id', '=', d['company_name'])], limit=1).display_name,
                'from_loc_name': self.env['stock.location'].search([('id', '=', d['from_loc_id'])], limit=1).display_name,
                'to_loc_name': self.env['stock.location'].search([('id', '=', d['to_loc_id'])], limit=1).display_name,
                'from_dept_name': self.env['hr.department'].search([('id', '=', d['from_dept_id'])], limit=1).display_name,
                'to_dept_name': self.env['hr.department'].search([('id', '=', d['to_dept_id'])], limit=1).display_name,
                'from_job_pos_name': self.env['hr.job'].search([('id', '=', d['from_job_pos'])], limit=1).display_name,
                'to_job_pos_name': self.env['hr.job'].search([('id', '=', d['to_job_pos'])], limit=1).display_name,
                'from_manager_name': self.env['hr.employee'].search([('id', '=', d['from_manager_id'])], limit=1).display_name,
                'to_manager_name': self.env['hr.employee'].search([('id', '=', d['to_manager_id'])], limit=1).display_name,
                'other_company_name': self.env['company.api.settings'].search([('id', '=', d['other_comp_name'])], limit=1).display_name,
                'other_company_job_location': d['other_comp_job_loc'],
                'other_company_dept_name': d['other_comp_dept'],
                'other_company_job_position': d['other_comp_job_pos'],
                'other_company_manager_name': d['other_comp_manager'],
                'note': d['remarks'],
            }
            data_list.append(vals)

        data = {
            'model': "employee.migration.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'month': dict(self._fields['month'].selection).get(self.month),
            'year': year,
            'transfer_company': transfer_company_val,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
        }
        return data
