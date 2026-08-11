from odoo import models, fields, api, _
import datetime
from datetime import datetime
from itertools import groupby
import xlsxwriter

import base64
from io import BytesIO


class LoanReportWizard(models.Model):
    _name = 'loan.report.wizard'
    _description = 'Loan Report Wizard'

    file_data = fields.Binary('Employee Loan Issue Detail')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Location', default=lambda self: self._get_work_loc(), domain=lambda self: self._set_domain_work_loc())
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

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

    def loan_report_pdf(self):
        employee_id = self.employee_id
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.loan_report_sql(employee_id, department_id, user_work_location_id)

        return self.env.ref(
            'custom_hr_report.loan_report_tmpl').with_context(landscape=False).report_action(self, data=data)

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

    def loan_report_excel(self):
        employee_id = self.employee_id
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id
        file_name = "Employee Loan Issue Detail.xlsx"
        file_pointer = BytesIO()

        # get data from sql
        data = self.loan_report_sql(employee_id, department_id, user_work_location_id)
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

                sheet.merge_range(0, 0, 0, 7, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 2, 7, 'Employee Loan Issue Detail', format0)

                sheet.merge_range(3, 0, 3, 3, 'Work/Job Location: {0}'.format(line[line2][0]['location_name']), format1)
                sheet.merge_range(3, 4, 3, 7, 'Department Name: {0}'.format(data['dept_name']), format3)

                sheet.write(4, 0, 'ID', format1)
                sheet.write(4, 1, 'Name', format1)
                sheet.write(4, 2, 'Loan No.', format2)
                sheet.write(4, 3, 'Loan Dt', format2)
                sheet.write(4, 4, 'Loan Amt', format3)
                sheet.write(4, 5, 'Adj Amt', format3)
                sheet.write(4, 6, 'Due Amt', format3)
                sheet.write(4, 7, 'Schedule Amt', format3)

                total_loan_amt = 0
                total_adj_amt = 0
                total_remain_amt = 0
                total_inst_amt = 0

                row = 5
                col = 0
                for line3 in line[line2]:
                    sheet.write(row, col, line3['id_no'], format4)
                    sheet.write(row, col + 1, line3['emp_name'], format4)
                    sheet.write(row, col + 2, line3['loan_no'], format5)
                    sheet.write(row, col + 3, datetime.strptime(str(line3['loan_date']), '%Y-%m-%d').strftime('%d-%b-%Y'), format5)
                    sheet.write(row, col + 4, round(line3['loan_amt'], 2), format6)
                    total_loan_amt = total_loan_amt + line3['loan_amt']
                    sheet.write(row, col + 5, round(line3['adj_amt'], 2), format6)
                    total_adj_amt = total_adj_amt + line3['adj_amt']
                    remain_amt = line3['loan_amt'] - line3['adj_amt']
                    sheet.write(row, col + 6, round(remain_amt, 2), format6)
                    total_remain_amt = total_remain_amt + remain_amt
                    sheet.write(row, col + 7, round(line3['inst_amt'], 2), format6)
                    total_inst_amt = total_inst_amt + line3['inst_amt']
                    row = row + 1

                final_row = row
                final_col = 0
                sheet.merge_range(final_row, final_col, final_row, final_col + 3, 'Total', format6)
                sheet.write(final_row, final_col + 4, round(total_loan_amt, 2), format6)
                sheet.write(final_row, final_col + 5, round(total_adj_amt, 2), format6)
                sheet.write(final_row, final_col + 6, round(total_remain_amt, 2), format6)
                sheet.write(final_row, final_col + 7, round(total_inst_amt,  2), format6)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Loan Issue Detail',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=loan.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def loan_report_sql(self, employee_id, department_id, user_work_location_id):

        employeeFilter = ""
        departmentFilter = ""
        locationFilter = ""
        dept_name = "All"
        work_location_name = "All"

        if employee_id:
            employeeFilter = "AND empl.employee_id = %s" % employee_id.id

        if department_id:
            departmentFilter = "AND empl.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            locationFilter = "AND hre.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        data_sql = """
                    SELECT hre.id_card_no AS id_no, hre.name AS emp_name, empl.loan_no AS loan_no, empl.start_date AS loan_date,
                    COALESCE(empl.loan_amount, 0) AS loan_amt, 
                    COALESCE(SUM(CASE WHEN lnstl.is_paid = 'True' THEN lnstl.installment_amt ELSE 0 END), 0) AS adj_amt,
                    COALESCE(empl.installment_amount, 0) AS inst_amt, COALESCE(hre.user_work_location_id, 100000) AS user_work_location_id, sl.name AS location_name
                    FROM employee_loan empl
                    JOIN installment_line lnstl ON lnstl.loan_id = empl.id
                    JOIN hr_employee hre ON hre.id = empl.employee_id
                    LEFT JOIN stock_location sl ON sl.id = hre.user_work_location_id
                    WHERE empl.state = 'done' AND empl.loan_no IS NOT NULL
                    {0} {1} {2}
                    GROUP BY hre.name, hre.id_card_no, empl.loan_no, empl.start_date, empl.loan_amount, empl.installment_amount, hre.user_work_location_id, sl.name
                    ORDER BY hre.id_card_no, hre.name, empl.loan_no, hre.user_work_location_id, sl.name
                    """.format(employeeFilter, departmentFilter, locationFilter)
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
            'model': 'loan.report.wizard',
            'form': self.read()[0],
            'csr': final_data_list,
            'work_loc_name': work_location_name,
            'dept_name': dept_name
        }

        return data
