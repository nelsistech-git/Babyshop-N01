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


class EmployeeDetailSalarySheetReportWizard(models.TransientModel):
    _name = "employee.detail.salary.sheet.report.wizard"
    _description = "Employee Detail Salary Sheet Report Wizard"

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

    file_data = fields.Binary('Employee Detail Salary Sheet Report Wizard')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       default=lambda self: self._get_work_loc(),
                                       domain=lambda self: self._set_domain_work_loc())
    employee_id = fields.Many2one('hr.employee', string='Employee')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', required=True)
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
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    include_zero_less_payable = fields.Boolean('With negative/zero payable')
    report_type = fields.Selection([
        ('all', 'All'),
        ('current_emp', 'Current Employee'),
        ('resign_emp', 'Resign Employee'),
    ], string='Report Type', default='all')

    # stamp = fields.Float(default=10.00, digits=(12, 2), string='Stamp')

    category_ids = fields.Many2many('hr.employee.category', 'employee_detail_salary_employee_category_rel', 
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

    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('Start date cannot be greater than the end date.'))

    @api.onchange('year', 'month')
    def _onchange_date_range(self):
        if self.month:
            m = int(self.month)
        else:
            m = datetime.today().month
        if self.year:
            y = int(self.year)
        else:
            y = datetime.today().year
        ndays = monthrange(y, m)[1]
        self.start_date = date(y, m, 1)
        self.end_date = date(y, m, ndays)

    def employee_detail_salary_sheet_report_pdf(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        state = self.state
        user_work_location_id = self.user_work_location_id
        include_zero_less_payable = self.include_zero_less_payable
        report_type = self.report_type
        employee_id = self.employee_id

        # get data from sql
        data = self.employee_detail_salary_sheet_report_sql(month, year, department_id, state, user_work_location_id,
                                                            include_zero_less_payable, report_type, employee_id)

        return self.env.ref(
            'custom_hr_report.employee_detail_salary_sheet_report_tmpl').with_context(landscape=True).report_action(
            self,
            data=data)

    def employee_detail_salary_sheet_report_excel(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        state = self.state
        user_work_location_id = self.user_work_location_id
        include_zero_less_payable = self.include_zero_less_payable
        report_type = self.report_type
        employee_id = self.employee_id

        # get data from sql
        data = self.employee_detail_salary_sheet_report_sql(month, year, department_id, state, user_work_location_id,
                                                            include_zero_less_payable, report_type, employee_id)

        file_name = "Employee Detail Salary Sheet Report (%s - %s).xlsx" % (data['month'], data['year'])
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

        total_emp = 0
        grand_total_basic_salary = 0
        grand_total_house_rent = 0
        grand_total_medical_alw = 0
        grand_total_con_alw = 0
        grand_total_gross_salary = 0
        grand_total_holy_day = 0
        grand_total_leave = 0
        grand_total_lwp = 0
        grand_total_abs_day = 0
        grand_total_present_day = 0
        grand_total_total_day_of_month = 0
        grand_total_abs_amt = 0
        grand_total_lwp_amt = 0
        grand_total_payable_salary = 0
        grand_total_tds = 0
        grand_total_advance_amount = 0
        grand_total_loan_adj = 0
        grand_total_pf = 0
        grand_total_stamp = 0
        grand_total_cash_payment = 0
        grand_total_bank_payment = 0

        if not data['form']['user_work_location_id']:
            summary_sheet = workbook.add_worksheet('Branch Summary')

            summary_sheet.merge_range(0, 0, 0, 26, "{0}".format(data['form']['company_id'][1]), format0)
            summary_sheet.merge_range(1, 0, 2, 26, 'Details salary sheet', format0)

            summary_sheet.write(3, 0, 'Branch', format1)
            summary_sheet.write(3, 1, 'Total Employee', format1)
            summary_sheet.write(3, 2, 'Basic', format3)
            summary_sheet.write(3, 3, 'House Rent', format3)
            summary_sheet.write(3, 4, 'Medical', format2)
            summary_sheet.write(3, 5, 'Con. Allowance', format3)
            summary_sheet.write(3, 6, 'Gross Salary', format2)

            summary_sheet.write(3, 7, 'Weekend + Public Holiday', format2)
            summary_sheet.write(3, 8, 'Leave', format2)
            summary_sheet.write(3, 9, 'LWP', format2)
            summary_sheet.write(3, 10, 'Absent (Abs+Punish+JR)', format2)
            summary_sheet.write(3, 11, 'OT Day', format2)
            summary_sheet.write(3, 12, 'Late Count', format2)
            summary_sheet.write(3, 13, 'Total Present Day', format2)
            summary_sheet.write(3, 14, 'Day of Month', format2)
            summary_sheet.write(3, 15, 'Absent Amount', format3)
            summary_sheet.write(3, 16, 'LWP Amount', format3)
            summary_sheet.write(3, 17, 'OT Amount', format3)

            summary_sheet.write(3, 18, 'Accrued Salary Payable', format3)

            summary_sheet.write(3, 19, 'Tax', format2)
            summary_sheet.write(3, 20, 'Advance Amount', format3)
            summary_sheet.write(3, 21, 'Loan Adjustment', format3)
            summary_sheet.write(3, 22, 'PF', format3)
            summary_sheet.write(3, 23, 'Stamp', format2)
            summary_sheet.write(3, 24, 'Late Amount', format2)
            summary_sheet.write(3, 25, 'Cash Payment', format3)
            summary_sheet.write(3, 26, 'Bank Payment', format3)

            summary_total_emp = 0
            summary_total_basic_salary = 0
            summary_total_house_rent = 0
            summary_total_medical_alw = 0
            summary_total_con_alw = 0
            summary_total_gross_salary = 0
            summary_total_holy_day = 0
            summary_total_leave = 0
            summary_total_lwp = 0
            summary_total_abs_day = 0
            summary_total_present_day = 0
            summary_total_total_day_of_month = 0
            summary_total_abs_amt = 0
            summary_total_lwp_amt = 0
            summary_total_payable_salary = 0
            summary_total_tds = 0
            summary_total_advance_amount = 0
            summary_total_loan_adj = 0
            summary_total_pf = 0
            summary_total_stamp = 0
            summary_total_cash_payment = 0
            summary_total_bank_payment = 0

            summary_row = 4
            summary_col = 0

            for line in data['summary_data_res']:
                summary_sheet.write(summary_row, summary_col, line['emp_work_location'], format4)
                summary_sheet.write(summary_row, summary_col + 1, line['total_emp'], format5)
                summary_total_emp = summary_total_emp + line['total_emp']
                summary_sheet.write(summary_row, summary_col + 2, line['basic_salary'], format6)
                summary_total_basic_salary = summary_total_basic_salary + line['basic_salary']
                summary_sheet.write(summary_row, summary_col + 3, line['house_rent'], format6)
                summary_total_house_rent = summary_total_house_rent + line['house_rent']
                summary_sheet.write(summary_row, summary_col + 4, line['medical_alw'], format6)
                summary_total_medical_alw = summary_total_medical_alw + line['medical_alw']
                summary_sheet.write(summary_row, summary_col + 5, line['con_alw'], format6)
                summary_total_con_alw = summary_total_con_alw + line['con_alw']
                summary_sheet.write(summary_row, summary_col + 6, line['gross_salary'], format6)
                summary_total_gross_salary = summary_total_gross_salary + line['gross_salary']
                summary_sheet.write(summary_row, summary_col + 7, line['holy_day'], format6)
                summary_total_holy_day = summary_total_holy_day + line['holy_day']

                summary_sheet.write(summary_row, summary_col + 8, line['no_overtime'], format6)
                summary_sheet.write(summary_row, summary_col + 9, line['actual_late'], format6)

                summary_sheet.write(summary_row, summary_col + 10, line['leave'], format6)
                summary_total_leave = summary_total_leave + line['leave']

                summary_sheet.write(summary_row, summary_col + 11, line['lwp'], format6)
                summary_total_lwp = summary_total_lwp + line['lwp']

                summary_sheet.write(summary_row, summary_col + 12, line['abs_day'], format6)
                summary_total_abs_day = summary_total_abs_day + line['abs_day']
                s_present_day = line['total_days']-line['leave']-line['holy_day']-line['abs_day']

                summary_sheet.write(summary_row, summary_col + 13, s_present_day, format6)
                summary_total_present_day = summary_total_present_day + s_present_day
                summary_sheet.write(summary_row, summary_col + 14, line['total_days'], format6)
                summary_total_total_day_of_month = summary_total_total_day_of_month + line['total_days']
                summary_sheet.write(summary_row, summary_col + 15, line['abs_amt'], format6)
                summary_total_abs_amt = summary_total_abs_amt + line['abs_amt']

                summary_sheet.write(summary_row, summary_col + 16, line['lwp_amt'], format6)
                summary_total_lwp_amt = summary_total_lwp_amt + line['lwp_amt']

                summary_sheet.write(summary_row, summary_col + 17, line['ota_alw'], format6)


                summary_sheet.write(summary_row, summary_col + 18, line['gross_salary'] - line['abs_amt'], format6)
                summary_total_payable_salary = summary_total_payable_salary + line['gross_salary'] - line['abs_amt']
                summary_sheet.write(summary_row, summary_col + 19, line['tds'], format6)
                summary_total_tds = summary_total_tds + line['tds']
                summary_sheet.write(summary_row, summary_col + 20, line['advance_amount'], format6)
                summary_total_advance_amount = summary_total_advance_amount + line['advance_amount']
                summary_sheet.write(summary_row, summary_col + 21, line['loan_adj'], format6)
                summary_total_loan_adj = summary_total_loan_adj + line['loan_adj']
                summary_sheet.write(summary_row, summary_col + 22, line['pf'], format6)
                summary_total_pf = summary_total_pf + line['pf']
                summary_sheet.write(summary_row, summary_col + 23, line['stamp'], format6)
                summary_total_stamp = summary_total_stamp + line['stamp']

                summary_sheet.write(summary_row, summary_col + 24, line['late_ded'], format6)

                summary_sheet.write(summary_row, summary_col + 25, line['cash_pay'], format6)
                summary_total_cash_payment = summary_total_cash_payment + line['cash_pay']
                summary_sheet.write(summary_row, summary_col + 26, line['bank_pay'], format6)
                summary_total_bank_payment = summary_total_bank_payment + line['bank_pay']

                summary_row = summary_row + 1

            summary_final_row = summary_row
            summary_final_col = 0
            summary_sheet.write(summary_final_row, summary_final_col, 'Total', format7)
            summary_sheet.write(summary_final_row, summary_final_col + 1, summary_total_emp, format9)
            summary_sheet.write(summary_final_row, summary_final_col + 2, summary_total_basic_salary, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 3, summary_total_house_rent, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 4, summary_total_medical_alw, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 5, summary_total_con_alw, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 6, summary_total_gross_salary, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 7, summary_total_holy_day, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 8, summary_total_leave, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 9, summary_total_lwp, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 10, summary_total_abs_day, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 11, '', format7)
            summary_sheet.write(summary_final_row, summary_final_col + 12, '', format7)
            summary_sheet.write(summary_final_row, summary_final_col + 13, summary_total_present_day, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 14, summary_total_total_day_of_month, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 15, summary_total_abs_amt, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 16, summary_total_lwp_amt, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 17, '', format7)
            summary_sheet.write(summary_final_row, summary_final_col + 18, summary_total_payable_salary, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 19, summary_total_tds, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 20, summary_total_advance_amount, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 21, summary_total_loan_adj, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 22, summary_total_pf, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 23, summary_total_stamp, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 24, '', format7)
            summary_sheet.write(summary_final_row, summary_final_col + 25, summary_total_cash_payment, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 26, summary_total_bank_payment, format7)

        for line in data['csr']:
            for line2 in line:
                sheet = workbook.add_worksheet(line[line2][0]['emp_work_location'])

                sheet.merge_range(0, 0, 0, 34, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 2, 34,
                                  "Employee Detail Salary Sheet Report (%s - %s)" % (data['start_date'], data['end_date']),
                                  format0)

                sheet.merge_range(3, 0, 3, 6, 'Work/Job Location: {0}'.format(line[line2][0]['emp_work_location']),
                                  format1)
                sheet.merge_range(3, 7, 3, 13, 'Status: {0}'.format(data['state_name']), format2)
                sheet.merge_range(3, 14, 3, 20, 'Department Name: {0}'.format(data['dept_name']), format2)
                sheet.merge_range(3, 21, 3, 27, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format2)
                sheet.merge_range(3, 28, 3, 34, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format3)


                sheet.merge_range(4, 0, 5, 0, 'Sl.', format2)
                sheet.merge_range(4, 1, 4, 7, 'Employee Information', format2)
                sheet.write(5, 1, 'Employee ID', format2)
                sheet.write(5, 2, 'Name', format1)
                sheet.write(5, 3, 'Joining Date', format2)
                sheet.write(5, 4, 'Department', format1)
                sheet.write(5, 5, 'Designation', format1)
                sheet.write(5, 6, 'Bank Account', format1)
                sheet.write(5, 7, 'Location', format1)

                sheet.merge_range(4, 8, 4, 12, 'Salary Information', format2)
                sheet.write(5, 8, 'Basic', format3)
                sheet.write(5, 9, 'House Rent', format3)
                sheet.write(5, 10, 'Medical', format2)
                sheet.write(5, 11, 'Con. Allowance', format3)
                sheet.write(5, 12, 'Gross Salary', format2)

                sheet.merge_range(4, 13, 4, 23, 'Attendance Information', format2)
                sheet.write(5, 13, 'Weekend + Public Holiday', format2)
                sheet.write(5, 14, 'Leave', format2)
                sheet.write(5, 15, 'LWP', format2)
                sheet.write(5, 16, 'Absent (Abs+Punish+JR)', format2)
                sheet.write(5, 17, 'OT Day', format2)
                sheet.write(5, 18, 'Late Count', format2)
                sheet.write(5, 19, 'Total Present Day', format2)
                sheet.write(5, 20, 'Day of Month', format2)
                sheet.write(5, 21, 'Absent Amount', format3)
                sheet.write(5, 22, 'LWP Amount', format3)
                sheet.write(5, 23, 'OT Amount', format3)

                sheet.merge_range(4, 24, 4, 24, 'Accrued Payable', format3)
                sheet.write(5, 24, 'Accrued Salary Payable', format3)

                sheet.merge_range(4, 25, 4, 30, 'Deduction', format2)
                sheet.write(5, 25, 'Tax', format2)
                sheet.write(5, 26, 'Advance Amount', format3)
                sheet.write(5, 27, 'Loan Adjustment', format3)
                sheet.write(5, 28, 'PF', format3)
                sheet.write(5, 29, 'Stamp', format2)
                sheet.write(5, 30, 'Late Amount', format2)
                sheet.merge_range(4, 31, 5, 31, 'Cash Payment', format3)
                sheet.merge_range(4, 32, 5, 32, 'Bank Payment', format3)
                sheet.merge_range(4, 33, 5, 33, 'Adjusted', format2)
                sheet.merge_range(4, 34, 5, 34, 'Signature', format2)

                row = 6
                col = 0

                sl_no = 1
                total_basic_salary = 0
                total_house_rent = 0
                total_medical_alw = 0
                total_con_alw = 0
                total_gross_salary = 0
                total_holy_day = 0
                total_leave = 0
                total_lwp = 0
                total_abs_day = 0
                total_present_day = 0
                total_total_day_of_month = 0
                total_abs_amt = 0
                total_lwp_amt = 0
                total_payable_salary = 0
                total_tds = 0
                total_advance_amount = 0
                total_loan_adj = 0
                total_pf = 0
                total_stamp = 0
                total_cash_payment = 0
                total_bank_payment = 0

                for line3 in line[line2]:
                    sheet.write(row, col + 0, sl_no, format5)
                    sheet.write(row, col + 1, line3['id_card_no'], format5)
                    sheet.write(row, col + 2, line3['employee_name'], format4)
                    joining_date = datetime.strptime(str(line3['joining_date']), '%Y-%m-%d').strftime('%d-%b-%Y') if line3['joining_date'] else None
                    sheet.write(row, col + 3, joining_date, format5)
                    sheet.write(row, col + 4, line3['dept_name'], format4)
                    sheet.write(row, col + 5, line3['emp_designation'], format4)
                    sheet.write(row, col + 6, line3['bank_ac'], format4)
                    sheet.write(row, col + 7, line3['emp_work_location'], format4)
                    sheet.write(row, col + 8, round(line3['basic_salary'], 2), format6)
                    total_basic_salary = total_basic_salary + line3['basic_salary']
                    grand_total_basic_salary = grand_total_basic_salary + line3['basic_salary']
                    sheet.write(row, col + 9, round(line3['house_rent'], 2), format6)
                    total_house_rent = total_house_rent + line3['house_rent']
                    grand_total_house_rent = grand_total_house_rent + line3['house_rent']
                    sheet.write(row, col + 10, round(line3['medical_alw'], 2), format6)
                    total_medical_alw = total_medical_alw + line3['medical_alw']
                    grand_total_medical_alw = grand_total_medical_alw + line3['medical_alw']
                    sheet.write(row, col + 11, round(line3['con_alw'], 2), format6)
                    total_con_alw = total_con_alw + line3['con_alw']
                    grand_total_con_alw = grand_total_con_alw + line3['con_alw']
                    sheet.write(row, col + 12, round(line3['gross_salary'], 2), format6)
                    total_gross_salary = total_gross_salary + line3['gross_salary']
                    grand_total_gross_salary = grand_total_gross_salary + line3['gross_salary']
                    sheet.write(row, col + 13, line3['holy_day'], format5)

                    total_holy_day = total_holy_day + line3['holy_day']
                    grand_total_holy_day = grand_total_holy_day + line3['holy_day']
                    sheet.write(row, col + 14, line3['leave'], format5)
                    total_leave = total_leave + line3['leave']
                    grand_total_leave = grand_total_leave + line3['leave']
                    sheet.write(row, col + 15, line3['leave_lwp'], format5)
                    total_lwp = total_lwp + line3['leave_lwp']
                    grand_total_lwp = grand_total_lwp + line3['leave_lwp']
                    sheet.write(row, col + 16, line3['abs_day'], format5)
                    total_abs_day = total_abs_day + line3['abs_day']
                    grand_total_abs_day = grand_total_abs_day + line3['abs_day']

                    sheet.write(row, col + 17, line3['no_overtime'], format5)
                    sheet.write(row, col + 18, line3['actual_late'], format5)

                    p_present_day = line3['total_days']-line3['leave']-line3['holy_day']-line3['abs_day']-line3['leave_lwp']
                    sheet.write(row, col + 19, p_present_day, format5)
                    total_present_day = total_present_day + p_present_day
                    grand_total_present_day = grand_total_present_day + p_present_day

                    sheet.write(row, col + 20, line3['total_days'], format5)
                    total_total_day_of_month = total_total_day_of_month + line3['total_days']
                    grand_total_total_day_of_month = grand_total_total_day_of_month + line3['total_days']
                    sheet.write(row, col + 21, round(line3['abs_amt'], 2), format6)
                    total_abs_amt = total_abs_amt + line3['abs_amt']
                    grand_total_abs_amt = grand_total_abs_amt + line3['abs_amt']
                    sheet.write(row, col + 22, round(line3['lwp_amt'], 2), format6)
                    total_lwp_amt = total_lwp_amt + line3['lwp_amt']
                    grand_total_lwp_amt = grand_total_lwp_amt + line3['lwp_amt']

                    sheet.write(row, col + 23, round(line3['ota_alw'], 2), format6)

                    sheet.write(row, col + 24, round(line3['gross_salary'] - line3['abs_amt'] - line3['lwp_amt'], 2), format6)
                    total_payable_salary = total_payable_salary + (line3['gross_salary'] - line3['abs_amt'] - line3['lwp_amt'])
                    grand_total_payable_salary = grand_total_payable_salary + (line3['gross_salary'] - line3['abs_amt'] - line3['lwp_amt'])
                    sheet.write(row, col + 25, round(line3['tds'], 2), format6)
                    total_tds = total_tds + line3['tds']
                    grand_total_tds = grand_total_tds + line3['tds']
                    sheet.write(row, col + 26, round(line3['advance_amount'], 2), format6)
                    total_advance_amount = total_advance_amount + line3['advance_amount']
                    grand_total_advance_amount = grand_total_advance_amount + line3['advance_amount']
                    sheet.write(row, col + 27, round(line3['loan_adj'], 2), format6)
                    total_loan_adj = total_loan_adj + line3['loan_adj']
                    grand_total_loan_adj = grand_total_loan_adj + line3['loan_adj']
                    sheet.write(row, col + 28, round(line3['pf'], 2), format6)
                    total_pf = total_pf + line3['pf']
                    grand_total_pf = grand_total_pf + line3['pf']
                    sheet.write(row, col + 29, round(line3['stamp'], 2), format5)
                    total_stamp = total_stamp + line3['stamp']
                    grand_total_stamp = grand_total_stamp + line3['stamp']

                    sheet.write(row, col + 30, round(line3['late_ded'], 2), format5)

                    sheet.write(row, col + 31, round(line3['cash_pay'], 2), format6)
                    total_cash_payment = total_cash_payment + line3['cash_pay']
                    grand_total_cash_payment = grand_total_cash_payment + line3['cash_pay']
                    sheet.write(row, col + 32, round(line3['bank_pay'], 2), format6)
                    total_bank_payment = total_bank_payment + line3['bank_pay']
                    grand_total_bank_payment = grand_total_bank_payment + line3['bank_pay']
                    sheet.write(row, col + 33, None, format5)
                    sheet.write(row, col + 34, None, format5)

                    row = row + 1
                    sl_no = sl_no + 1
                    total_emp = total_emp + 1

                final_row = row
                final_col = 0

                sheet.merge_range(final_row, final_col, final_row, final_col + 7, 'TOTAL', format7)
                sheet.write(final_row, final_col + 8, total_basic_salary, format7)
                sheet.write(final_row, final_col + 9, total_house_rent, format7)
                sheet.write(final_row, final_col + 10, total_medical_alw, format7)
                sheet.write(final_row, final_col + 11, total_con_alw, format7)
                sheet.write(final_row, final_col + 12, total_gross_salary, format7)
                sheet.write(final_row, final_col + 13, total_holy_day, format9)
                sheet.write(final_row, final_col + 14, total_leave, format9)
                sheet.write(final_row, final_col + 15, total_lwp, format9)
                sheet.write(final_row, final_col + 16, total_abs_day, format9)
                sheet.write(final_row, final_col + 17, '', format9)
                sheet.write(final_row, final_col + 18, '', format9)
                sheet.write(final_row, final_col + 19, total_present_day, format9)
                sheet.write(final_row, final_col + 20, total_total_day_of_month, format9)
                sheet.write(final_row, final_col + 21, total_abs_amt, format7)
                sheet.write(final_row, final_col + 22, total_lwp_amt, format7)
                sheet.write(final_row, final_col + 23, '', format7)
                sheet.write(final_row, final_col + 24, total_payable_salary, format7)
                sheet.write(final_row, final_col + 25, total_tds, format7)
                sheet.write(final_row, final_col + 26, total_advance_amount, format7)
                sheet.write(final_row, final_col + 27, total_loan_adj, format7)
                sheet.write(final_row, final_col + 28, total_pf, format7)
                sheet.write(final_row, final_col + 29, total_stamp, format9)
                sheet.write(final_row, final_col + 30, '', format9)
                sheet.write(final_row, final_col + 31, total_cash_payment, format7)
                sheet.write(final_row, final_col + 32, total_bank_payment, format7)
                sheet.merge_range(final_row, final_col + 33, final_row, final_col + 34, None, format7)

        sheet = workbook.add_worksheet('Grand Total')

        sheet.merge_range(0, 0, 0, 20, 'GRAND TOTAL', format9)
        sheet.write(1, 0, 'Total Employee', format7)
        sheet.write(1, 1, 'Basic', format3)
        sheet.write(1, 2, 'House Rent', format3)
        sheet.write(1, 3, 'Medical', format2)
        sheet.write(1, 4, 'Con. Allowance', format3)
        sheet.write(1, 5, 'Gross Salary', format2)

        sheet.write(1, 6, 'Weekend + Public Holiday', format2)
        sheet.write(1, 7, 'Leave', format2)
        sheet.write(1, 8, 'Absent (Abs+Punish+JR)', format2)
        sheet.write(1, 9, 'Total Present Day', format2)
        sheet.write(1, 10, 'Day of Month', format2)
        sheet.write(1, 11, 'Absent Amount', format3)
        sheet.write(1, 12, 'Accrued Salary Payable', format3)

        sheet.write(1, 13, 'Tax', format2)
        sheet.write(1, 14, 'Advance Amount', format3)
        sheet.write(1, 15, 'Loan Adjustment', format3)
        sheet.write(1, 16, 'PF', format3)
        sheet.write(1, 17, 'Stamp', format2)
        sheet.write(1, 18, 'Cash Payment', format3)
        sheet.write(1, 19, 'Bank Payment', format3)

        sheet.write(2, 0, total_emp, format9)
        sheet.write(2, 1, grand_total_basic_salary, format7)
        sheet.write(2, 2, grand_total_house_rent, format7)
        sheet.write(2, 3, grand_total_medical_alw, format7)
        sheet.write(2, 4, grand_total_con_alw, format7)
        sheet.write(2, 5, grand_total_gross_salary, format7)
        sheet.write(2, 6, grand_total_holy_day, format7)
        sheet.write(2, 7, grand_total_leave, format7)
        sheet.write(2, 8, grand_total_abs_day, format7)
        sheet.write(2, 9, grand_total_present_day, format7)
        sheet.write(2, 10, grand_total_total_day_of_month, format7)
        sheet.write(2, 11, grand_total_abs_amt, format7)
        sheet.write(2, 12, grand_total_payable_salary, format7)
        sheet.write(2, 13, grand_total_tds, format7)
        sheet.write(2, 14, grand_total_advance_amount, format7)
        sheet.write(2, 15, grand_total_loan_adj, format7)
        sheet.write(2, 16, grand_total_pf, format7)
        sheet.write(2, 17, grand_total_stamp, format7)
        sheet.write(2, 18, grand_total_cash_payment, format7)
        sheet.write(2, 19, grand_total_bank_payment, format7)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Detail Salary Sheet Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.detail.salary.sheet.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_detail_salary_sheet_report_sql(self, month, year, department_id, state, user_work_location_id, include_zero_less_payable, report_type, employee_id):
        # m = int(month)
        # y = int(year)
        # ndays = monthrange(y, m)[1]
        # start_date = date(y, m, 1)
        # end_date = date(y, m, ndays)
        start_date = self.start_date
        end_date = self.end_date
        delta = (end_date - start_date).days + 1

        if delta > 31:
            raise ValidationError('Unable to process due to date range is more than 31 days.')

        state_filter = ""
        dept_filter = ""
        dept_filter2 = ""
        work_loc_filter = ""
        emp_filter = ""
        state_name = ""
        include_non_zero_payable_filter = ""
        report_type_filter = ""
        dept_name = "All"
        work_location_name = "All"
        emp_name = "All"
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "tbl1.emp_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "tbl1.emp_id_card"
        # print(order_by)

        if state:
            state_filter = "AND hp.state = '%s'" % state
            state_name = dict(self._fields['state'].selection).get(self.state)

        if department_id:
            dept_filter = "WHERE tbl1.dept_id = %s" % department_id.id
            dept_filter2 = "AND hp.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            work_loc_filter = "AND hp.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if employee_id:
            emp_filter = "AND he.id = %s" % employee_id.id
            emp_name = employee_id.display_name

        if not include_zero_less_payable:
            include_non_zero_payable_filter = "AND (hp.cash_amount > 0 OR hp.bank_amount > 0)"

        if report_type == 'current_emp':
            report_type_filter = "AND he.resigned = False"
        elif report_type == 'resign_emp':
            report_type_filter = "AND he.resigned = True"

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND he.sbu_unit_id = {0}".format(self.sbu_unit_id.id)  

        data_sql = """
                    SELECT tbl1.emp_id, tbl1.emp_name AS employee_name, tbl1.emp_id_card AS id_card_no, tbl1.emp_joining_date AS joining_date, hd.name->>'en_US' AS dept_name,hj.name->>'en_US' AS emp_designation, COALESCE(tbl1.work_loc_id, 100000) AS work_loc_id, sl.name AS emp_work_location, tbl1.bank_ac,
                    COALESCE(SUM(tbl1.basic), 0) AS basic_salary,
                    COALESCE(SUM(tbl1.house_rent), 0) AS house_rent,
                    COALESCE(SUM(tbl1.medical_alw), 0) AS medical_alw,
                    COALESCE(SUM(tbl1.con_alw), 0) AS con_alw,
                    COALESCE(SUM(tbl1.ota_alw), 0) AS ota_alw,
                    COALESCE(SUM(tbl1.gross), 0) AS gross_salary,
                    COALESCE(SUM(tbl2.holy_day), 0) AS holy_day,
                    COALESCE(SUM(tbl1.pf), 0) AS pf,
                    COALESCE(SUM(tbl2.leave_count), 0) AS leave,
                    COALESCE(SUM(tbl2.leave_lwp), 0) AS leave_lwp,
                    COALESCE(SUM(tbl2.absent_day), 0) AS abs_day,
                    COALESCE(SUM(tbl2.no_presence),0) AS no_presence,
                    COALESCE(SUM(tbl2.work_days),0) AS work_days,
                    COALESCE(SUM(tbl2.no_join_resign),0) AS no_join_resign,
                    COALESCE(SUM(tbl2.total_days),0) AS total_days,
                    COALESCE(SUM(tbl2.no_overtime),0) AS no_overtime,
                    COALESCE(SUM(tbl2.actual_late),0) AS actual_late,
                    COALESCE(SUM(tbl2.ab_amt), 0) AS abs_amt,
                    COALESCE(SUM(tbl2.lwp_amt), 0) AS lwp_amt,
                    COALESCE(SUM(tbl2.late_in_abs), 0) AS late_in_abs,
                    --COALESCE((tbl1.gross / tbl2.total_days) * tbl2.leave_lwp, 0) AS lwp_amt,
                    COALESCE(SUM(tbl1.total_payable_sal), 0) AS payable_salary,
                    COALESCE(SUM(tbl1.adv_salary),0) AS advance_amount,
                    COALESCE(SUM(tbl1.loan_adj),0) AS loan_adj,
                    COALESCE(SUM(tbl1.tds),0) AS tds,
                    tbl1.payment_type AS payment_type,
                    COALESCE(SUM(tbl1.stamp), 0) AS stamp,
                    COALESCE(SUM(tbl1.late_ded), 0) AS late_ded,
                    COALESCE(SUM(tbl1.bank_pay), 0) AS bank_pay,
                    COALESCE(SUM(tbl1.cash_pay), 0) AS cash_pay,
                    COALESCE(SUM(tbl1.late_abs), 0) AS late_abs
                    FROM(
                        SELECT he.id AS emp_id, he.name AS emp_name, he.id_card_no AS emp_id_card, he.initial_employment_date AS emp_joining_date, he.department_id AS dept_id, he.job_id AS des_id, he.s_bank_account_no as bank_ac,
                        he.user_work_location_id AS work_loc_id, 
                        
                        --COALESCE(ast.no_absence + ast.actual_late_count + ast.actual_diff_count + ast.no_join_resign_ded_count, 0) AS absent_day,
                        --ast.no_presence AS present_day,
                        --ast.no_of_days AS day_of_month,
                        --ast.no_join_resign_ded_count AS day_join_resign,
                        --ast.no_of_total_days AS day_of_range,
                        --COALESCE((ast.no_absence + ast.actual_late_count + ast.actual_diff_count + ast.no_join_resign_ded_count) * ast.per_day_salary, 0) AS ab_amt,
                        
                        SUM(CASE WHEN hpl.code = 'BASIC' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS basic,
                        SUM(CASE WHEN hpl.code = 'HRA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS house_rent,
                        SUM(CASE WHEN hpl.code = 'MEDICAL' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS medical_alw,
                        SUM(CASE WHEN hpl.code = 'TA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS con_alw,
                        SUM(CASE WHEN hpl.code in ('OT','OVT','OTA') THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS ota_alw,
                        SUM(CASE WHEN hpl.code = 'GROSS' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS gross,
                        SUM(CASE WHEN hpl.code = 'NET' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS total_payable_sal,
                        SUM(CASE WHEN hpl.code = 'SAR' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS adv_salary,
                        SUM(CASE WHEN hpl.code in ('LOANINS', 'LOANINT') THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS loan_adj,
                        SUM(CASE WHEN hpl.code = 'PF' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS pf,
                        --hc.stamp_deduction AS stamp, hc.tds_deduction AS tds,
                        SUM(CASE WHEN hpl.code = 'TDS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS tds,
                        SUM(CASE WHEN hpl.code = 'STMP' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS stamp,
                        SUM(CASE WHEN hpl.code = 'LATE' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS late_ded,
                        SUM(CASE WHEN hpl.code = 'LWP' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS lwp_ded,
                        SUM(CASE WHEN hpl.code = 'ABSL' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS late_abs,
                        hp.disbursement_type AS payment_type, hp.bank_amount AS bank_pay, hp.cash_amount AS cash_pay
                        FROM hr_employee he
                        --LEFT JOIN hr_contract hc ON hc.employee_id = he.id
                        --LEFT JOIN (SELECT * FROM attendance_sheet WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}') ast ON ast.employee_id = he.id
                        LEFT JOIN hr_payslip hp ON hp.employee_id = he.id
                        LEFT JOIN hr_payslip_line hpl ON hpl.slip_id = hp.id
                        LEFT JOIN hr_payroll_structure hps ON hps.id = hp.struct_id
                        {10} JOIN (
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {9}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = he.id                        
                        WHERE hps.code = 'BASE' AND DATE(hp.date_to) BETWEEN '{0}' AND '{1}' {2} 
                        --AND hc.state = 'open'
                        {3} {4} {5} {6} {7} {8}
                        GROUP BY he.id, he.name, he.id_card_no, he.initial_employment_date, hp.department_id, hp.disbursement_type, hp.cash_amount, hp.bank_amount, he.s_bank_account_no, he.job_id, hp.user_work_location_id
                        --ast.no_absence, ast.no_presence, ast.no_of_days,ast.no_join_resign_ded_count,ast.no_of_total_days,ast.actual_diff_count,ast.actual_late_count, ast.per_day_salary
                        ) tbl1
                        
                        LEFT JOIN (
                            --SELECT employee_id, 
                                --    COALESCE((no_weekend+no_ph), 0) AS holy_day,
                                --    COALESCE((no_cl+no_ml+no_pl), 0) AS leave_count,
                                --    COALESCE(no_lwp, 0) AS unpaid_leave_count
                                --   FROM attendance_sheet
                                --    WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}'
                                
                                SELECT employee_id,
                                    SUM(COALESCE(no_of_days, 0)) AS work_days,
                                    SUM(COALESCE(no_of_total_days, 0)) AS total_days,
                                    SUM(COALESCE(no_weekend, 0)) AS holy_day_wk,
                                    SUM(COALESCE(no_ph, 0)) AS holy_day_ph,
                                    SUM(COALESCE((no_weekend+no_ph), 0)) AS holy_day,
                                    SUM(COALESCE(no_cl, 0)) AS leave_cl,
                                    SUM(COALESCE(no_ml, 0)) AS leave_ml,
                                    SUM(COALESCE(no_pl, 0)) AS leave_pl,
                                    SUM(COALESCE(no_lwp, 0)) AS leave_lwp,
                                    SUM(COALESCE((no_cl+no_ml+no_pl), 0)) AS leave_count,
                                    SUM(COALESCE(no_presence, 0)) AS no_presence,
                                    SUM(COALESCE(no_absence, 0)) AS no_absence,
                                    SUM(COALESCE(actual_late_count, 0)) AS actual_late,
                                    SUM(COALESCE(actual_diff_count, 0)) AS actual_early_out,
                                    SUM(COALESCE(no_join_resign_ded_count, 0)) AS no_join_resign,
                                    SUM(COALESCE(no_overtime, 0)) AS no_overtime,
                                    SUM(COALESCE(no_late_abs, 0)) AS late_in_abs,
                                    SUM(COALESCE(no_absence + actual_late_count + actual_diff_count + no_join_resign_ded_count, 0)) AS absent_day,
                                    SUM(COALESCE((no_absence + actual_late_count + actual_diff_count + no_join_resign_ded_count) * per_day_salary, 0)) AS ab_amt,
                                    SUM(COALESCE(no_lwp * per_day_salary, 0)) AS lwp_amt
                                    FROM attendance_sheet
                                    WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}'
                                GROUP BY employee_id
                                
                        ) tbl2 ON tbl2.employee_id = tbl1.emp_id    
                        
                    LEFT JOIN hr_department hd ON hd.id = tbl1.dept_id
                    LEFT JOIN hr_job hj ON hj.id = tbl1.des_id
                    LEFT JOIN stock_location sl ON sl.id = tbl1.work_loc_id
                    GROUP BY tbl1.emp_id, tbl1.emp_name, tbl1.payment_type, tbl1.emp_id_card, tbl1.emp_joining_date, hd.name, hj.name, sl.name, tbl1.work_loc_id, tbl1.bank_ac,tbl1.gross,tbl2.work_days,tbl2.total_days,tbl2.leave_lwp
                    -- ORDER BY tbl1.emp_id_card, tbl1.emp_name
                    ORDER BY {11}, tbl1.emp_name
                    """.format(start_date, end_date,
                                state_filter, dept_filter2,
                                work_loc_filter, include_non_zero_payable_filter,
                                report_type_filter, emp_filter,
                                business_unit_filter, tags_filter,
                                tag_filter_join, order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        # define a fuction for key
        def key_func(k):
            return k['work_loc_id']

        data_list = sorted(data_res, key=key_func)

        final_data_list = []

        for key, value in groupby(data_list, key_func):
            vals = {
                key: list(value)
            }
            final_data_list.append(vals)

        summary_data_sql = """
                            SELECT COALESCE(COUNT(tbl1.emp_id), 0) AS total_emp, COALESCE(tbl1.work_loc_id, 100000) AS work_loc_id, sl.name AS emp_work_location, 
                            COALESCE(SUM(tbl1.basic), 0) AS basic_salary,
                            COALESCE(SUM(tbl1.house_rent), 0) AS house_rent,
                            COALESCE(SUM(tbl1.medical_alw), 0) AS medical_alw,
                            COALESCE(SUM(tbl1.con_alw), 0) AS con_alw,
                            COALESCE(SUM(tbl1.ota_alw), 0) AS ota_alw,
                            COALESCE(SUM(tbl1.gross), 0) AS gross_salary,
                            COALESCE(SUM(tbl2.holy_day), 0) AS holy_day,
                            COALESCE(SUM(tbl1.pf), 0) AS pf,
                            COALESCE(SUM(tbl2.leave_count), 0) AS leave,
                            COALESCE(SUM(tbl2.leave_lwp), 0) AS lwp,
                            COALESCE(SUM(tbl2.absent_day), 0) AS abs_day,
                            COALESCE(SUM(tbl2.no_presence),0) AS no_presence,
                            COALESCE(SUM(tbl2.work_days),0) AS work_days,
                            COALESCE(SUM(tbl2.no_join_resign),0) AS no_join_resign,
                            COALESCE(SUM(tbl2.total_days),0) AS total_days,
                            COALESCE(SUM(tbl2.no_overtime),0) AS no_overtime,
                            COALESCE(SUM(tbl2.actual_late),0) AS actual_late,
                            COALESCE(SUM(tbl2.ab_amt), 0) AS abs_amt,
                            COALESCE(SUM(tbl2.lwp_amt), 0) AS lwp_amt,
                            COALESCE(SUM(tbl2.late_in_abs), 0) AS late_in_abs,
                            COALESCE(SUM(tbl1.total_payable_sal), 0) AS payable_salary,
                            COALESCE(SUM(tbl1.adv_salary),0) AS advance_amount,
                            COALESCE(SUM(tbl1.loan_adj),0) AS loan_adj,
                            COALESCE(SUM(tbl1.tds),0) AS tds,
                            COALESCE(SUM(tbl1.stamp), 0) AS stamp,
                            COALESCE(SUM(tbl1.late_ded), 0) AS late_ded,
                            COALESCE(SUM(tbl1.bank_pay), 0) AS bank_pay,
                            COALESCE(SUM(tbl1.cash_pay), 0) AS cash_pay,
                            COALESCE(SUM(tbl1.late_abs), 0) AS late_abs
                            FROM(
                                SELECT he.id AS emp_id, hp.user_work_location_id AS work_loc_id,
                                --COALESCE(ast.no_absence + ast.actual_late_count + ast.actual_diff_count + ast.no_join_resign_ded_count, 0) AS absent_day,
                                --ast.no_presence AS no_presence,
                                --ast.no_of_days AS day_of_month,
                                --ast.no_join_resign_ded_count AS day_join_resign,
                                --ast.no_of_total_days AS day_of_range,
                                he.department_id AS dept_id,
                                --COALESCE((ast.no_absence + ast.actual_late_count + ast.actual_diff_count + ast.no_join_resign_ded_count) * ast.per_day_salary, 0) AS ab_amt,
                                --COALESCE(ast.no_lwp * ast.per_day_salary, 0) AS lwp_amt,
                                
                                SUM(CASE WHEN hpl.code = 'BASIC' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS basic,
                                SUM(CASE WHEN hpl.code = 'HRA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS house_rent,
                                SUM(CASE WHEN hpl.code = 'MEDICAL' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS medical_alw,
                                SUM(CASE WHEN hpl.code = 'TA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS con_alw,
                                SUM(CASE WHEN hpl.code in ('OT','OVT','OTA') THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS ota_alw,
                                SUM(CASE WHEN hpl.code = 'GROSS' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS gross,
                                SUM(CASE WHEN hpl.code = 'NET' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS total_payable_sal,
                                SUM(CASE WHEN hpl.code = 'SAR' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS adv_salary,
                                SUM(CASE WHEN hpl.code in ('LOANINS', 'LOANINT') THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS loan_adj,
                                SUM(CASE WHEN hpl.code = 'PF' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS pf,
                                SUM(CASE WHEN hpl.code = 'TDS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS tds,
                                SUM(CASE WHEN hpl.code = 'STMP' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS stamp,
                                SUM(CASE WHEN hpl.code = 'LATE' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS late_ded,
                                SUM(CASE WHEN hpl.code = 'LWP' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS lwp_ded,
                                SUM(CASE WHEN hpl.code = 'ABSL' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS late_abs,
                                hp.bank_amount AS bank_pay, hp.cash_amount AS cash_pay
                                
                                FROM hr_employee he
                                --LEFT JOIN hr_contract hc ON hc.employee_id = he.id
                                LEFT JOIN (SELECT * FROM attendance_sheet WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}') ast ON ast.employee_id = he.id
                                LEFT JOIN hr_payslip hp ON hp.employee_id = he.id
                                LEFT JOIN hr_payslip_line hpl ON hpl.slip_id = hp.id
                                LEFT JOIN hr_payroll_structure hps ON hps.id = hp.struct_id
                                {10} JOIN (
                                    SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                    JOIN hr_employee_category etag on etag.id=ecr.category_id
                                    {9}
                                    GROUP BY emp_id
                                ) emp_tag ON emp_tag.emp_id = he.id                          
                                WHERE hps.code = 'BASE' AND DATE(hp.date_to) BETWEEN '{0}' AND '{1}' {2}
                                 --AND hc.state = 'open'
                                {4} {5} {6} {7} {8}
                                GROUP BY he.id, hp.cash_amount, hp.bank_amount, hp.user_work_location_id
                                --, ast.no_absence, ast.no_presence, ast.no_of_days,ast.no_join_resign_ded_count,ast.no_of_total_days,ast.actual_diff_count, ast.actual_late_count, ast.no_lwp, ast.per_day_salary
                                ) tbl1
                            
                            LEFT JOIN (
                                --SELECT employee_id, 
                                --    COALESCE((no_weekend+no_ph), 0) AS holy_day,
                                --    COALESCE((no_cl+no_ml+no_pl), 0) AS leave_count,
                                --    COALESCE(no_lwp, 0) AS unpaid_leave_count
                                --   FROM attendance_sheet
                                --    WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}'
                                
                                SELECT employee_id,
                                    SUM(COALESCE(no_of_days, 0)) AS work_days,
                                    SUM(COALESCE(no_of_total_days, 0)) AS total_days,
                                    SUM(COALESCE(no_weekend, 0)) AS holy_day_wk,
                                    SUM(COALESCE(no_ph, 0)) AS holy_day_ph,
                                    SUM(COALESCE((no_weekend+no_ph), 0)) AS holy_day,
                                    SUM(COALESCE(no_cl, 0)) AS leave_cl,
                                    SUM(COALESCE(no_ml, 0)) AS leave_ml,
                                    SUM(COALESCE(no_pl, 0)) AS leave_pl,
                                    SUM(COALESCE(no_lwp, 0)) AS leave_lwp,
                                    SUM(COALESCE((no_cl+no_ml+no_pl), 0)) AS leave_count,
                                    SUM(COALESCE(no_presence, 0)) AS no_presence,
                                    SUM(COALESCE(no_absence, 0)) AS no_absence,
                                    SUM(COALESCE(actual_late_count, 0)) AS actual_late,
                                    SUM(COALESCE(actual_diff_count, 0)) AS actual_early_out,
                                    SUM(COALESCE(no_join_resign_ded_count, 0)) AS no_join_resign,
                                    SUM(COALESCE(no_overtime, 0)) AS no_overtime,
                                    SUM(COALESCE(no_late_abs, 0)) AS late_in_abs,
                                    SUM(COALESCE(no_absence + actual_late_count + actual_diff_count + no_join_resign_ded_count, 0)) AS absent_day,
                                    SUM(COALESCE((no_absence + actual_late_count + actual_diff_count + no_join_resign_ded_count) * per_day_salary, 0)) AS ab_amt,
                                    SUM(COALESCE(no_lwp * per_day_salary, 0)) AS lwp_amt
                                    
                                    FROM attendance_sheet
                                    WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}'
                                GROUP BY employee_id
                                
                            ) tbl2 ON tbl2.employee_id = tbl1.emp_id  
                            
                            LEFT JOIN stock_location sl ON sl.id = tbl1.work_loc_id
                            {3}
                            GROUP BY sl.name, tbl1.work_loc_id
                            ORDER BY sl.name
                            """.format(start_date, end_date,
                                        state_filter, dept_filter, 
                                        work_loc_filter, include_non_zero_payable_filter, 
                                        report_type_filter, emp_filter, business_unit_filter, tags_filter, tag_filter_join)
        self.env.cr.execute(summary_data_sql)
        summary_data_res = self.env.cr.dictfetchall()

        data = {
            'model': "employee.detail.salary.sheet.report.wizard",
            'form': self.read()[0],
            'csr': final_data_list,
            'summary_data_res': summary_data_res,
            'month': dict(self._fields['month'].selection).get(self.month),
            'year': year,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'emp_name': emp_name,
            'state_name': state_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data

    def salary_details_sheet_report_sql_new(self, month, year, department_id, state, user_work_location_id,
                                        include_zero_less_payable, report_type, employee_id):

        start_date = self.start_date
        end_date = self.end_date
        delta = (end_date - start_date).days + 1

        if delta > 31:
            raise ValidationError('Unable to process due to date range is more than 31 days.')

        state_filter = ""
        dept_filter = ""
        dept_filter2 = ""
        work_loc_filter = ""
        emp_filter = ""
        state_name = ""
        include_non_zero_payable_filter = ""
        report_type_filter = ""
        dept_name = "All"
        work_location_name = "All"
        emp_name = "All"

        if state:
            state_filter = "AND hp.state = '%s'" % state
            state_name = dict(self._fields['state'].selection).get(self.state)

        if department_id:
            dept_filter = "WHERE tbl1.dept_id = %s" % department_id.id
            dept_filter2 = "AND hp.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            work_loc_filter = "AND hp.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if employee_id:
            emp_filter = "AND he.id = %s" % employee_id.id
            emp_name = employee_id.display_name

        if not include_zero_less_payable:
            include_non_zero_payable_filter = "AND (hp.cash_amount > 0 OR hp.bank_amount > 0)"

        if report_type == 'current_emp':
            report_type_filter = "AND he.resigned = False"
        elif report_type == 'resign_emp':
            report_type_filter = "AND he.resigned = True"

        data_sql = """
                    SELECT tbl1.sal_struct as salary_struct, COALESCE(tbl1.work_loc_id, 100000) AS work_loc_id, sl.name AS emp_work_location, 
                    hd.name->>'en_US' AS dept_name,hj.name->>'en_US' AS emp_designation, 
                    tbl1.emp_id, tbl1.emp_name as employee_name, tbl1.emp_id_card as id_card_no, tbl1.emp_joining_date as joining_date, 

                    COALESCE(SUM(tbl1.basic), 0) AS basic_salary, 
                    COALESCE(SUM(tbl1.house_rent), 0) AS house_rent,
                    COALESCE(SUM(tbl1.medical_alw), 0) AS medical_alw, 
                    COALESCE(SUM(tbl1.con_alw), 0) AS con_alw, 
                    COALESCE(SUM(tbl1.dearness_alw), 0) AS dearness_alw, 
                    COALESCE(SUM(tbl1.food_alw), 0) AS food_alw, 
                    COALESCE(SUM(tbl1.mobile_alw), 0) AS mobile_alw, 
                    COALESCE(SUM(tbl1.car_alw), 0) AS car_alw, 
                    COALESCE(SUM(tbl1.lfa_alw), 0) AS lfa_alw, 
                    COALESCE(SUM(tbl1.salbonus_alw), 0) AS salbonus_alw, 
                    COALESCE(SUM(tbl1.tiffin_alw), 0) AS tiffin_alw, 
                    COALESCE(SUM(tbl1.att_bonus_alw), 0) AS att_bonus_alw, 
                    COALESCE(SUM(tbl1.other_alw), 0) AS other_alw, 
                    COALESCE(SUM(tbl1.extra_alw), 0) AS extra_alw, 
                    COALESCE(SUM(tbl1.daily_alw), 0) AS daily_alw, 
                    COALESCE(SUM(tbl1.ota_alw), 0) AS ota_alw, 
                    COALESCE(SUM(tbl1.sp_house_rent), 0) AS sp_house_rent, 
                    COALESCE(SUM(tbl1.arr_alw), 0) AS arr_alw, 
                    COALESCE(SUM(tbl1.bonus_alw), 0) AS bonus_alw, 
                    COALESCE(SUM(tbl1.gross_sal), 0) AS gross_salary,
                    COALESCE(SUM(tbl1.pf_ded), 0) AS pf_ded, 
                    COALESCE(SUM(tbl1.tds_ded), 0) AS tds_ded,
                    COALESCE(SUM(tbl1.adv_sal_ded), 0) AS adv_sal_ded, 
                    COALESCE(SUM(tbl1.loan_ded), 0) AS loan_ded,
                    COALESCE(SUM(tbl1.loan_inst_ded), 0) AS loan_int_ded, 
                    COALESCE(SUM(tbl1.stamp_ded), 0) AS stamp_ded,
                    COALESCE(SUM(tbl1.absent_ded), 0) AS absent_ded, 
                    COALESCE(SUM(tbl1.join_res_ded), 0) AS join_res_ded,
                    COALESCE(SUM(tbl1.lwp_ded), 0) AS lwp_ded, 
                    COALESCE(SUM(tbl1.disp_ded), 0) AS disp_ded,
                    COALESCE(SUM(tbl1.medical_leave_ded), 0) AS medical_leave_ded, 
                    COALESCE(SUM(tbl1.insur_ded), 0) AS insur_ded,
                    COALESCE(SUM(tbl1.late_ded), 0) AS late_in_ded, 
                    COALESCE(SUM(tbl1.diff_ded), 0) AS early_out_ded,
                    COALESCE(SUM(tbl1.total_net_sal), 0) AS total_net_sal,
                    tbl1.payment_type, 
                    COALESCE(SUM(tbl1.bank_pay), 0) AS bank_pay, COALESCE(SUM(tbl1.cash_pay), 0) AS cash_pay,
                    tbl1.emp_sal_acc,

                    COALESCE(SUM(tbl2.work_days), 0) AS work_days,
                    COALESCE(SUM(tbl2.total_days), 0) AS total_days,
                    COALESCE(SUM(tbl2.holy_day_wk), 0) AS holy_day_wk,
                    COALESCE(SUM(tbl2.holy_day_ph), 0) AS holy_day_ph,
                    COALESCE(SUM(tbl2.leave_cl), 0) AS leave_cl,
                    COALESCE(SUM(tbl2.leave_ml), 0) AS leave_ml,
                    COALESCE(SUM(tbl2.leave_pl), 0) AS leave_pl,
                    COALESCE(SUM(tbl2.leave_lwp), 0) AS leave_lwp,
                    COALESCE(SUM(tbl2.no_presence), 0) AS no_presence,
                    COALESCE(SUM(tbl2.no_absence), 0) AS no_absence,
                    COALESCE(SUM(tbl2.actual_late), 0) AS actual_late,
                    COALESCE(SUM(tbl2.actual_early_out), 0) AS actual_early_out,
                    COALESCE(SUM(tbl2.no_join_resign), 0) AS no_join_resign,
                    COALESCE(SUM(tbl2.no_overtime), 0) AS no_overtime
                    FROM(
                        SELECT hps.name AS sal_struct,
                        hp.user_work_location_id AS work_loc_id, 
                        hp.department_id AS dept_id, 
                        he.job_id AS desig_id, 
                        he.id AS emp_id, 
                        he.name AS emp_name, 
                        he.id_card_no AS emp_id_card, 
                        he.initial_employment_date AS emp_joining_date, 

                        SUM(CASE WHEN hpl.code = 'BASIC' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS basic,
                        SUM(CASE WHEN hpl.code = 'HRA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS house_rent,
                        SUM(CASE WHEN hpl.code = 'MEDICAL' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS medical_alw,
                        SUM(CASE WHEN hpl.code = 'TA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS con_alw,
                        SUM(CASE WHEN hpl.code = 'DA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS dearness_alw,
                        SUM(CASE WHEN hpl.code = 'MEAL' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS food_alw,
                        SUM(CASE WHEN hpl.code = 'MOBILE' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS mobile_alw,
                        SUM(CASE WHEN hpl.code = 'CARA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS car_alw,
                        SUM(CASE WHEN hpl.code = 'LFA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS lfa_alw,
                        SUM(CASE WHEN hpl.code = 'SALBA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS salbonus_alw,
                        SUM(CASE WHEN hpl.code = 'TIFFIN' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS tiffin_alw,
                        SUM(CASE WHEN hpl.code = 'ATTBONUS' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS att_bonus_alw,
                        SUM(CASE WHEN hpl.code = 'OTHER' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS other_alw,
                        SUM(CASE WHEN hpl.code = 'EA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS extra_alw,
                        SUM(CASE WHEN hpl.code = 'DLA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS daily_alw,
                        SUM(CASE WHEN hpl.code in ('OT','OVT','OTA') THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS ota_alw,
                        SUM(CASE WHEN hpl.code = 'SPHRA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS sp_house_rent,
                        SUM(CASE WHEN hpl.code = 'ARR' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS arr_alw,
                        SUM(CASE WHEN hpl.code in ('BONUS','FESTBONUS','SPBONUS') THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS bonus_alw,
                        SUM(CASE WHEN hpl.code = 'GROSS' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS gross_sal,
                        
                        SUM(CASE WHEN hpl.code = 'PF' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS pf_ded,
                        SUM(CASE WHEN hpl.code = 'TDS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS tds_ded,
                        SUM(CASE WHEN hpl.code = 'SAR' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS adv_sal_ded,
                        SUM(CASE WHEN hpl.code = 'LOANINS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS loan_ded,
                        SUM(CASE WHEN hpl.code = 'LOANINT' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS loan_inst_ded,
                        SUM(CASE WHEN hpl.code = 'STMP' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS stamp_ded,
                        SUM(CASE WHEN hpl.code = 'ABS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS absent_ded,
                        SUM(CASE WHEN hpl.code = 'JRD' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS join_res_ded,
                        SUM(CASE WHEN hpl.code = 'LWP' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS lwp_ded,
                        SUM(CASE WHEN hpl.code = 'DISP' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS disp_ded,
                        SUM(CASE WHEN hpl.code = 'ML' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS medical_leave_ded,
                        SUM(CASE WHEN hpl.code = 'INSUR' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS insur_ded,
                        SUM(CASE WHEN hpl.code = 'LATE' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS late_ded,
                        SUM(CASE WHEN hpl.code = 'DIFF' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS diff_ded,
                        SUM(CASE WHEN hpl.code = 'NET' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS total_net_sal,
                        hp.disbursement_type AS payment_type,
                        hp.bank_amount AS bank_pay, 
                        hp.cash_amount AS cash_pay,
                        he.s_bank_account_no as emp_sal_acc

                        FROM hr_payslip hp
                        LEFT JOIN hr_payslip_line hpl ON hpl.slip_id = hp.id
                        LEFT JOIN hr_payroll_structure hps ON hps.id = hp.struct_id       
                        LEFT JOIN hr_employee he ON he.id = hp.employee_id
                        --LEFT JOIN hr_contract hc ON hc.id = hp.contract_id
                        WHERE hps.regular_pay = True AND DATE(hp.date_to) BETWEEN '{0}' AND '{1}' {2}
                        {3} {4} {5} {6} {7}
                        GROUP BY hps.name, hp.user_work_location_id, hp.department_id, he.job_id, he.id, he.name, he.id_card_no, he.initial_employment_date, 
                        hp.disbursement_type, hp.bank_amount, hp.cash_amount, he.s_bank_account_no

                        ) tbl1
                        LEFT JOIN (
                            SELECT employee_id,
                                SUM(COALESCE(no_of_days, 0)) AS work_days,
                                SUM(COALESCE(no_of_total_days, 0)) AS total_days,
                                SUM(COALESCE(no_weekend, 0)) AS holy_day_wk,
                                SUM(COALESCE(no_ph, 0)) AS holy_day_ph,
                                SUM(COALESCE(no_cl, 0)) AS leave_cl,
                                SUM(COALESCE(no_ml, 0)) AS leave_ml,
                                SUM(COALESCE(no_pl, 0)) AS leave_pl,
                                SUM(COALESCE(no_lwp, 0)) AS leave_lwp,
                                SUM(COALESCE(no_presence, 0)) AS no_presence,
                                SUM(COALESCE(no_absence, 0)) AS no_absence,
                                SUM(COALESCE(actual_late_count, 0)) AS actual_late,
                                SUM(COALESCE(actual_diff_count, 0)) AS actual_early_out,
                                SUM(COALESCE(no_join_resign_ded_count, 0)) AS no_join_resign,
                                SUM(COALESCE(no_overtime, 0)) AS no_overtime
                                FROM attendance_sheet
                                WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}'
                                GROUP BY employee_id
                        ) tbl2 ON tbl2.employee_id = tbl1.emp_id

                    LEFT JOIN hr_department hd ON hd.id = tbl1.dept_id
                    LEFT JOIN hr_job hj ON hj.id = tbl1.desig_id
                    LEFT JOIN stock_location sl ON sl.id = tbl1.work_loc_id

                    GROUP BY tbl1.sal_struct, tbl1.work_loc_id, sl.name, hd.name, hj.name, tbl1.emp_id, tbl1.emp_name, tbl1.emp_id_card, tbl1.emp_joining_date, tbl1.payment_type, tbl1.emp_sal_acc
                    ORDER BY tbl1.emp_id_card, tbl1.emp_name
                    """.format(start_date, end_date, state_filter, dept_filter2, work_loc_filter,
                               include_non_zero_payable_filter, report_type_filter, emp_filter)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        # define a fuction for key
        def key_func(k):
            return k['work_loc_id']

        data_list = sorted(data_res, key=key_func)

        final_data_list = []

        for key, value in groupby(data_list, key_func):
            vals = {
                key: list(value)
            }
            final_data_list.append(vals)

        summary_data_sql = """
                            SELECT COALESCE(COUNT(tbl1.emp_id), 0) AS total_emp, COALESCE(tbl1.work_loc_id, 100000) AS work_loc_id, sl.name AS emp_work_location, 
                            tbl1.sal_struct AS sal_struct,
                            COALESCE(SUM(tbl1.basic), 0) AS basic_salary, 
                            COALESCE(SUM(tbl1.house_rent), 0) AS house_rent,
                            COALESCE(SUM(tbl1.medical_alw), 0) AS medical_alw, 
                            COALESCE(SUM(tbl1.con_alw), 0) AS con_alw, 
                            COALESCE(SUM(tbl1.dearness_alw), 0) AS dearness_alw, 
                            COALESCE(SUM(tbl1.food_alw), 0) AS food_alw, 
                            COALESCE(SUM(tbl1.mobile_alw), 0) AS mobile_alw, 
                            COALESCE(SUM(tbl1.car_alw), 0) AS car_alw, 
                            COALESCE(SUM(tbl1.lfa_alw), 0) AS lfa_alw, 
                            COALESCE(SUM(tbl1.salbonus_alw), 0) AS salbonus_alw, 
                            COALESCE(SUM(tbl1.tiffin_alw), 0) AS tiffin_alw, 
                            COALESCE(SUM(tbl1.att_bonus_alw), 0) AS att_bonus_alw, 
                            COALESCE(SUM(tbl1.other_alw), 0) AS other_alw, 
                            COALESCE(SUM(tbl1.extra_alw), 0) AS extra_alw, 
                            COALESCE(SUM(tbl1.daily_alw), 0) AS daily_alw, 
                            COALESCE(SUM(tbl1.ota_alw), 0) AS ota_alw, 
                            COALESCE(SUM(tbl1.sp_house_rent), 0) AS sp_house_rent, 
                            COALESCE(SUM(tbl1.arr_alw), 0) AS arr_alw, 
                            COALESCE(SUM(tbl1.bonus_alw), 0) AS bonus_alw, 
                            COALESCE(SUM(tbl1.gross_sal), 0) AS gross_salary,
                            COALESCE(SUM(tbl1.pf_ded), 0) AS pf_ded, 
                            COALESCE(SUM(tbl1.tds_ded), 0) AS tds_ded,
                            COALESCE(SUM(tbl1.adv_sal_ded), 0) AS adv_sal_ded, 
                            COALESCE(SUM(tbl1.loan_ded), 0) AS loan_ded,
                            COALESCE(SUM(tbl1.loan_inst_ded), 0) AS loan_int_ded, 
                            COALESCE(SUM(tbl1.stamp_ded), 0) AS stamp_ded,
                            COALESCE(SUM(tbl1.absent_ded), 0) AS absent_ded, 
                            COALESCE(SUM(tbl1.join_res_ded), 0) AS join_res_ded,
                            COALESCE(SUM(tbl1.lwp_ded), 0) AS lwp_ded, 
                            COALESCE(SUM(tbl1.disp_ded), 0) AS disp_ded,
                            COALESCE(SUM(tbl1.medical_leave_ded), 0) AS medical_leave_ded, 
                            COALESCE(SUM(tbl1.insur_ded), 0) AS insur_ded,
                            COALESCE(SUM(tbl1.late_ded), 0) AS late_in_ded, 
                            COALESCE(SUM(tbl1.diff_ded), 0) AS early_out_ded,
                            COALESCE(SUM(tbl1.total_net_sal), 0) AS total_net_sal,
                            COALESCE(SUM(tbl1.bank_pay), 0) AS bank_pay,
                            COALESCE(SUM(tbl1.cash_pay), 0) AS cash_pay,

                            COALESCE(SUM(tbl2.work_days), 0) AS work_days,
                            COALESCE(SUM(tbl2.total_days), 0) AS total_days,
                            COALESCE(SUM(tbl2.holy_day_wk), 0) AS holy_day_wk,
                            COALESCE(SUM(tbl2.holy_day_ph), 0) AS holy_day_ph,
                            COALESCE(SUM(tbl2.leave_cl), 0) AS leave_cl,
                            COALESCE(SUM(tbl2.leave_ml), 0) AS leave_ml,
                            COALESCE(SUM(tbl2.leave_pl), 0) AS leave_pl,
                            COALESCE(SUM(tbl2.leave_lwp), 0) AS leave_lwp,
                            COALESCE(SUM(tbl2.no_presence), 0) AS no_presence,
                            COALESCE(SUM(tbl2.no_absence), 0) AS no_absence,
                            COALESCE(SUM(tbl2.actual_late), 0) AS actual_late,
                            COALESCE(SUM(tbl2.actual_early_out), 0) AS actual_early_out,
                            COALESCE(SUM(tbl2.no_join_resign), 0) AS no_join_resign,
                            COALESCE(SUM(tbl2.no_overtime), 0) AS no_overtime

                            FROM(
                                SELECT hps.name AS sal_struct,
                                hp.user_work_location_id AS work_loc_id, 
                                hp.department_id AS dept_id, 
                                he.job_id AS desig_id, 
                                he.id AS emp_id, 
                                he.name AS emp_name, 
                                he.id_card_no AS emp_id_card, 
                                he.initial_employment_date AS emp_joining_date, 

                                SUM(CASE WHEN hpl.code = 'BASIC' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS basic,
                                SUM(CASE WHEN hpl.code = 'HRA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS house_rent,
                                SUM(CASE WHEN hpl.code = 'MEDICAL' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS medical_alw,
                                SUM(CASE WHEN hpl.code = 'TA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS con_alw,
                                SUM(CASE WHEN hpl.code = 'DA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS dearness_alw,
                                SUM(CASE WHEN hpl.code = 'MEAL' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS food_alw,
                                SUM(CASE WHEN hpl.code = 'MOBILE' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS mobile_alw,
                                SUM(CASE WHEN hpl.code = 'CARA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS car_alw,
                                SUM(CASE WHEN hpl.code = 'LFA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS lfa_alw,
                                SUM(CASE WHEN hpl.code = 'SALBA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS salbonus_alw,
                                SUM(CASE WHEN hpl.code = 'TIFFIN' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS tiffin_alw,
                                SUM(CASE WHEN hpl.code = 'ATTBONUS' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS att_bonus_alw,
                                SUM(CASE WHEN hpl.code = 'OTHER' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS other_alw,
                                SUM(CASE WHEN hpl.code = 'EA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS extra_alw,
                                SUM(CASE WHEN hpl.code = 'DLA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS daily_alw,
                                SUM(CASE WHEN hpl.code in ('OT','OVT','OTA') THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS ota_alw,
                                SUM(CASE WHEN hpl.code = 'SPHRA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS sp_house_rent,
                                SUM(CASE WHEN hpl.code = 'ARR' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS arr_alw,
                                SUM(CASE WHEN hpl.code in ('BONUS','FESTBONUS','SPBONUS') THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS bonus_alw,
                                SUM(CASE WHEN hpl.code = 'GROSS' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS gross_sal,

                                SUM(CASE WHEN hpl.code = 'PF' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS pf_ded,
                                SUM(CASE WHEN hpl.code = 'TDS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS tds_ded,
                                SUM(CASE WHEN hpl.code = 'SAR' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS adv_sal_ded,
                                SUM(CASE WHEN hpl.code = 'LOANINS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS loan_ded,
                                SUM(CASE WHEN hpl.code = 'LOANINT' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS loan_inst_ded,
                                SUM(CASE WHEN hpl.code = 'STMP' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS stamp_ded,
                                SUM(CASE WHEN hpl.code = 'ABS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS absent_ded,
                                SUM(CASE WHEN hpl.code = 'JRD' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS join_res_ded,
                                SUM(CASE WHEN hpl.code = 'LWP' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS lwp_ded,
                                SUM(CASE WHEN hpl.code = 'DISP' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS disp_ded,
                                SUM(CASE WHEN hpl.code = 'ML' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS medical_leave_ded,
                                SUM(CASE WHEN hpl.code = 'INSUR' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS insur_ded,
                                SUM(CASE WHEN hpl.code = 'LATE' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS late_ded,
                                SUM(CASE WHEN hpl.code = 'DIFF' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS diff_ded,
                                SUM(CASE WHEN hpl.code = 'NET' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS total_net_sal,
                                hp.disbursement_type AS payment_type,
                                hp.bank_amount AS bank_pay, 
                                hp.cash_amount AS cash_pay,
                                he.s_bank_account_no as emp_sal_acc
                                FROM hr_payslip hp
                                LEFT JOIN hr_payslip_line hpl ON hpl.slip_id = hp.id
                                LEFT JOIN hr_payroll_structure hps ON hps.id = hp.struct_id       
                                LEFT JOIN hr_employee he ON he.id = hp.employee_id
                                WHERE hps.regular_pay = True AND DATE(hp.date_to) BETWEEN '{0}' AND '{1}' {2}
                                {3} {4} {5} {6} {7}
                                GROUP BY hps.name, hp.user_work_location_id, hp.department_id, he.job_id, he.id, he.name, he.id_card_no, he.initial_employment_date, 
                                hp.disbursement_type, hp.bank_amount, hp.cash_amount, he.s_bank_account_no
                                ) tbl1

                                LEFT JOIN (
                                    SELECT employee_id,
                                        SUM(COALESCE(no_of_days, 0)) AS work_days,
                                        SUM(COALESCE(no_of_total_days, 0)) AS total_days,
                                        SUM(COALESCE(no_weekend, 0)) AS holy_day_wk,
                                        SUM(COALESCE(no_ph, 0)) AS holy_day_ph,
                                        SUM(COALESCE(no_cl, 0)) AS leave_cl,
                                        SUM(COALESCE(no_ml, 0)) AS leave_ml,
                                        SUM(COALESCE(no_pl, 0)) AS leave_pl,
                                        SUM(COALESCE(no_lwp, 0)) AS leave_lwp,
                                        SUM(COALESCE(no_presence, 0)) AS no_presence,
                                        SUM(COALESCE(no_absence, 0)) AS no_absence,
                                        SUM(COALESCE(actual_late_count, 0)) AS actual_late,
                                        SUM(COALESCE(actual_diff_count, 0)) AS actual_early_out,
                                        SUM(COALESCE(no_join_resign_ded_count, 0)) AS no_join_resign,
                                        SUM(COALESCE(no_overtime, 0)) AS no_overtime
                                        FROM attendance_sheet
                                        WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}'
                                        GROUP BY employee_id                
                                ) tbl2 ON tbl2.employee_id = tbl1.emp_id

                            LEFT JOIN stock_location sl ON sl.id = tbl1.work_loc_id                            
                            GROUP BY sl.name, tbl1.work_loc_id, tbl1.sal_struct
                            ORDER BY sl.name, tbl1.sal_struct
                            """.format(start_date, end_date, state_filter, dept_filter2, work_loc_filter,
                                       include_non_zero_payable_filter, report_type_filter, emp_filter)
        self.env.cr.execute(summary_data_sql)
        summary_data_res = self.env.cr.dictfetchall()

        data = {
            'model': "salary.details.sheet.report.wizard",
            'form': self.read()[0],
            'csr': final_data_list,
            'summary_data_res': summary_data_res,
            'month': dict(self._fields['month'].selection).get(self.month),
            'year': year,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'emp_name': emp_name,
            'state_name': state_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
            
        }
        return data