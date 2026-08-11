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
    work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       default=lambda self: self._get_work_loc(),
                                       domain=lambda self: self._set_domain_work_loc())
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

    @api.model
    def _set_domain_work_loc(self):
        if self.env.user.user_work_location_id:
            return [('is_work_loc', '=', True), ('state', '=', 'done'),
                    ('id', '=', self.env.user.user_work_location_id.id)]
        else:
            return [('is_work_loc', '=', True), ('state', '=', 'done')]

    @api.model
    def _get_work_loc(self):
        if self.env.user.work_location_id:
            return self.env.user.work_location_id.id

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
        work_location_id = self.work_location_id
        include_zero_less_payable = self.include_zero_less_payable
        report_type = self.report_type

        # get data from sql
        data = self.employee_detail_salary_sheet_report_sql(month, year, department_id, state, work_location_id,
                                                            include_zero_less_payable, report_type)

        return self.env.ref(
            'custom_hr_report.employee_detail_salary_sheet_report_tmpl').with_context(landscape=True).report_action(
            self,
            data=data)

    def employee_detail_salary_sheet_report_excel(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        state = self.state
        work_location_id = self.work_location_id
        include_zero_less_payable = self.include_zero_less_payable
        report_type = self.report_type

        # get data from sql
        data = self.employee_detail_salary_sheet_report_sql(month, year, department_id, state, work_location_id,
                                                            include_zero_less_payable, report_type)

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

            summary_sheet.merge_range(0, 0, 0, 19, "{0}".format(data['form']['company_id'][1]), format0)
            summary_sheet.merge_range(1, 0, 2, 19, 'Bonus Sheet', format0)

            summary_sheet.write(3, 0, 'Branch', format1)
            summary_sheet.write(3, 1, 'Total Employee', format1)
            summary_sheet.write(3, 2, 'Basic', format3)
            summary_sheet.write(3, 3, 'House Rent', format3)
            summary_sheet.write(3, 4, 'Medical', format2)
            summary_sheet.write(3, 5, 'Con. Allowance', format3)
            summary_sheet.write(3, 6, 'Gross Salary', format2)
            summary_sheet.write(3, 7, 'Holy Day(Friday + Occasion)', format2)
            summary_sheet.write(3, 8, 'Leave', format2)
            # summary_sheet.write(3, 8, 'LWP', format2)
            summary_sheet.write(3, 9, 'Absent Day', format2)
            summary_sheet.write(3, 10, 'Total Present Day', format2)
            summary_sheet.write(3, 11, 'Day of Month', format2)
            summary_sheet.write(3, 12, 'Absent Amount', format3)
            summary_sheet.write(3, 13, 'Accrued Salary Payable', format3)
            summary_sheet.write(3, 14, 'Tax', format2)
            summary_sheet.write(3, 15, 'Advance Amount', format3)
            summary_sheet.write(3, 16, 'Loan Adjustment', format3)
            summary_sheet.write(3, 17, 'PF', format3)
            summary_sheet.write(3, 18, 'Stamp', format2)
            summary_sheet.write(3, 19, 'Cash Payment', format3)
            summary_sheet.write(3, 20, 'Bank Payment', format3)

            summary_total_emp = 0
            summary_total_basic_salary = 0
            summary_total_house_rent = 0
            summary_total_medical_alw = 0
            summary_total_con_alw = 0
            summary_total_gross_salary = 0
            summary_total_holy_day = 0
            summary_total_leave = 0
            summary_total_abs_day = 0
            summary_total_present_day = 0
            summary_total_total_day_of_month = 0
            summary_total_abs_amt = 0
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
                summary_sheet.write(summary_row, summary_col + 8, line['leave'], format6)
                summary_total_leave = summary_total_leave + line['leave']
                summary_sheet.write(summary_row, summary_col + 9, line['abs_day'], format6)
                summary_total_abs_day = summary_total_abs_day + line['abs_day']
                summary_sheet.write(summary_row, summary_col + 10, line['present_day'], format6)
                summary_total_present_day = summary_total_present_day + line['present_day']
                summary_sheet.write(summary_row, summary_col + 11, line['total_day_of_month'], format6)
                summary_total_total_day_of_month = summary_total_total_day_of_month + line['total_day_of_month']
                summary_sheet.write(summary_row, summary_col + 12, line['abs_amt'], format6)
                summary_total_abs_amt = summary_total_abs_amt + line['abs_amt']
                summary_sheet.write(summary_row, summary_col + 13, line['gross_salary'] - line['abs_amt'], format6)
                summary_total_payable_salary = summary_total_payable_salary + line['gross_salary'] - line['abs_amt']
                summary_sheet.write(summary_row, summary_col + 14, line['tds'], format6)
                summary_total_tds = summary_total_tds + line['tds']
                summary_sheet.write(summary_row, summary_col + 15, line['advance_amount'], format6)
                summary_total_advance_amount = summary_total_advance_amount + line['advance_amount']
                summary_sheet.write(summary_row, summary_col + 16, line['loan_adj'], format6)
                summary_total_loan_adj = summary_total_loan_adj + line['loan_adj']
                summary_sheet.write(summary_row, summary_col + 17, line['pf'], format6)
                summary_total_pf = summary_total_pf + line['pf']
                summary_sheet.write(summary_row, summary_col + 18, line['stamp'], format6)
                summary_total_stamp = summary_total_stamp + line['stamp']
                summary_sheet.write(summary_row, summary_col + 19, line['cash_pay'], format6)
                summary_total_cash_payment = summary_total_cash_payment + line['cash_pay']
                summary_sheet.write(summary_row, summary_col + 20, line['bank_pay'], format6)
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
            summary_sheet.write(summary_final_row, summary_final_col + 9, summary_total_abs_day, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 10, summary_total_present_day, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 11, summary_total_total_day_of_month, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 12, summary_total_abs_amt, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 13, summary_total_payable_salary, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 14, summary_total_tds, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 15, summary_total_advance_amount, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 16, summary_total_loan_adj, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 17, summary_total_pf, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 18, summary_total_stamp, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 19, summary_total_cash_payment, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 20, summary_total_bank_payment, format7)

        for line in data['csr']:
            for line2 in line:
                sheet = workbook.add_worksheet(line[line2][0]['emp_work_location'])

                sheet.merge_range(0, 0, 0, 30, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 2, 30,
                                  "Employee Detail Salary Sheet Report (%s - %s)" % (data['start_date'], data['end_date']),
                                  format0)

                sheet.merge_range(3, 0, 3, 9, 'Work/Job Location: {0}'.format(line[line2][0]['emp_work_location']),
                                  format1)
                sheet.merge_range(3, 10, 3, 19, 'Status: {0}'.format(data['state_name']), format2)
                sheet.merge_range(3, 20, 3, 30, 'Department Name: {0}'.format(data['dept_name']), format3)

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
                sheet.merge_range(4, 13, 4, 20, '', format2)
                sheet.write(5, 13, 'Holy Day(Friday + Occasion)', format2)
                sheet.write(5, 14, 'Leave', format2)
                sheet.write(5, 15, 'LWP', format2)
                sheet.write(5, 16, 'Absent Day', format2)
                sheet.write(5, 17, 'Total Present Day', format2)
                sheet.write(5, 18, 'Day of Month', format2)
                sheet.write(5, 19, 'Absent Amount', format3)
                sheet.write(5, 20, 'LWP Amount', format3)
                sheet.merge_range(4, 21, 4, 26, 'Deduct', format2)
                sheet.write(5, 21, 'Accrued Salary Payable', format3)
                sheet.write(5, 22, 'Tax', format2)
                sheet.write(5, 23, 'Advance Amount', format3)
                sheet.write(5, 24, 'Loan Adjustment', format3)
                sheet.write(5, 25, 'PF', format3)
                sheet.write(5, 26, 'Stamp', format2)
                sheet.merge_range(4, 27, 5, 27, 'Cash Payment', format3)
                sheet.merge_range(4, 28, 5, 28, 'Bank Payment', format3)
                sheet.merge_range(4, 29, 5, 29, 'Adjusted', format2)
                sheet.merge_range(4, 30, 5, 30, 'Signature', format2)

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
                    joining_date = datetime.strptime(str(line3['joining_date']), '%Y-%m-%d').strftime('%d-%b-%Y') if \
                    line3['joining_date'] else None
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
                    sheet.write(row, col + 15, line3['unpaid_leave_count'], format5)
                    total_lwp = total_lwp + line3['unpaid_leave_count']
                    grand_total_lwp = grand_total_lwp + line3['unpaid_leave_count']
                    sheet.write(row, col + 16, line3['abs_day'], format5)
                    total_abs_day = total_abs_day + line3['abs_day']
                    grand_total_abs_day = grand_total_abs_day + line3['abs_day']
                    sheet.write(row, col + 17, line3['present_day'], format5)
                    total_present_day = total_present_day + line3['present_day']
                    grand_total_present_day = grand_total_present_day + line3['present_day']
                    sheet.write(row, col + 18, line3['total_day_of_month'], format5)
                    total_total_day_of_month = total_total_day_of_month + line3['total_day_of_month']
                    grand_total_total_day_of_month = grand_total_total_day_of_month + line3['total_day_of_month']
                    sheet.write(row, col + 19, round(line3['abs_amt'], 2), format6)
                    total_abs_amt = total_abs_amt + line3['abs_amt']
                    grand_total_abs_amt = grand_total_abs_amt + line3['abs_amt']
                    sheet.write(row, col + 20, round(line3['lwp_amt'], 2), format6)
                    total_lwp_amt = total_lwp_amt + line3['lwp_amt']
                    grand_total_lwp_amt = grand_total_lwp_amt + line3['lwp_amt']
                    sheet.write(row, col + 21, round(line3['gross_salary'] - line3['abs_amt'] - line3['lwp_amt'], 2), format6)
                    total_payable_salary = total_payable_salary + (line3['gross_salary'] - line3['abs_amt'] - line3['lwp_amt'])
                    grand_total_payable_salary = grand_total_payable_salary + (line3['gross_salary'] - line3['abs_amt'] - line3['lwp_amt'])
                    sheet.write(row, col + 22, round(line3['tds'], 2), format6)
                    total_tds = total_tds + line3['tds']
                    grand_total_tds = grand_total_tds + line3['tds']
                    sheet.write(row, col + 23, round(line3['advance_amount'], 2), format6)
                    total_advance_amount = total_advance_amount + line3['advance_amount']
                    grand_total_advance_amount = grand_total_advance_amount + line3['advance_amount']
                    sheet.write(row, col + 24, round(line3['loan_adj'], 2), format6)
                    total_loan_adj = total_loan_adj + line3['loan_adj']
                    grand_total_loan_adj = grand_total_loan_adj + line3['loan_adj']
                    sheet.write(row, col + 26, round(line3['pf'], 2), format6)
                    total_pf = total_pf + line3['pf']
                    grand_total_pf = grand_total_pf + line3['pf']
                    sheet.write(row, col + 26, round(line3['stamp'], 2), format5)
                    total_stamp = total_stamp + line3['stamp']
                    grand_total_stamp = grand_total_stamp + line3['stamp']
                    sheet.write(row, col + 27, round(line3['cash_pay'], 2), format6)
                    total_cash_payment = total_cash_payment + line3['cash_pay']
                    grand_total_cash_payment = grand_total_cash_payment + line3['cash_pay']
                    sheet.write(row, col + 28, round(line3['bank_pay'], 2), format6)
                    total_bank_payment = total_bank_payment + line3['bank_pay']
                    grand_total_bank_payment = grand_total_bank_payment + line3['bank_pay']
                    sheet.write(row, col + 29, None, format5)
                    sheet.write(row, col + 30, None, format5)

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
                sheet.write(final_row, final_col + 17, total_present_day, format9)
                sheet.write(final_row, final_col + 18, total_total_day_of_month, format9)
                sheet.write(final_row, final_col + 19, total_abs_amt, format7)
                sheet.write(final_row, final_col + 20, total_lwp_amt, format7)
                sheet.write(final_row, final_col + 21, total_payable_salary, format7)
                sheet.write(final_row, final_col + 22, total_tds, format7)
                sheet.write(final_row, final_col + 23, total_advance_amount, format7)
                sheet.write(final_row, final_col + 24, total_loan_adj, format7)
                sheet.write(final_row, final_col + 25, total_pf, format7)
                sheet.write(final_row, final_col + 26, total_stamp, format9)
                sheet.write(final_row, final_col + 27, total_cash_payment, format7)
                sheet.write(final_row, final_col + 28, total_bank_payment, format7)
                sheet.merge_range(final_row, final_col + 29, final_row, final_col + 30, None, format7)

        sheet = workbook.add_worksheet('Grand Total')

        sheet.merge_range(0, 0, 0, 20, 'GRAND TOTAL', format9)
        sheet.write(1, 0, 'Total Employee', format7)
        sheet.write(1, 1, 'Basic', format3)
        sheet.write(1, 2, 'House Rent', format3)
        sheet.write(1, 3, 'Medical', format2)
        sheet.write(1, 4, 'Con. Allowance', format3)
        sheet.write(1, 5, 'Gross Salary', format2)
        sheet.write(1, 6, 'Holy Day(Friday + Occasion)', format2)
        sheet.write(1, 7, 'Leave', format2)
        sheet.write(1, 8, 'Absent Day', format2)
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

    def employee_detail_salary_sheet_report_sql(self, month, year, department_id, state, work_location_id, include_zero_less_payable, report_type):
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
        state_name = ""
        include_non_zero_payable_filter = ""
        report_type_filter = ""
        dept_name = "All"
        work_location_name = "All"

        if state:
            state_filter = "AND hp.state = '%s'" % state
            state_name = dict(self._fields['state'].selection).get(self.state)

        if department_id:
            dept_filter = "WHERE tbl1.dept_id = %s" % department_id.id
            dept_filter2 = "AND he.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if work_location_id:
            work_loc_filter = "AND he.work_location_id = %s" % work_location_id.id
            work_location_name = work_location_id.display_name

        if not include_zero_less_payable:
            include_non_zero_payable_filter = "AND (hp.cash_amount > 0 OR hp.bank_amount > 0)"

        if report_type == 'current_emp':
            report_type_filter = "AND he.resigned = False"
        elif report_type == 'resign_emp':
            report_type_filter = "AND he.resigned = True"

        data_sql = """
                    SELECT tbl1.emp_id, tbl1.emp_name AS employee_name, tbl1.emp_id_card AS id_card_no, tbl1.emp_joining_date AS joining_date, hd.name->>'en_US' AS dept_name,hj.name->>'en_US' AS emp_designation, COALESCE(tbl1.work_loc_id, 100000) AS work_loc_id, sl.name AS emp_work_location, tbl1.bank_ac, COALESCE(SUM(tbl1.basic), 0) AS basic_salary, COALESCE(SUM(tbl1.house_rent), 0) AS house_rent,
                    COALESCE(SUM(tbl1.medical_alw), 0) AS medical_alw, COALESCE(SUM(tbl1.con_alw), 0) AS con_alw, COALESCE(SUM(tbl1.gross), 0) AS gross_salary, COALESCE(SUM(tbl2.holy_day), 0) AS holy_day, COALESCE(SUM(tbl1.pf), 0) AS pf,
                    COALESCE(SUM(tbl3.leave_count), 0) AS leave,COALESCE(SUM(tbl4.unpaid_leave_count), 0) AS unpaid_leave_count, COALESCE(SUM(tbl1.absent_day), 0) AS abs_day, COALESCE(SUM(tbl1.present_day),0) AS present_day, COALESCE(SUM(tbl1.day_of_month),0) AS total_day_of_month,
                    COALESCE(SUM(tbl1.ab_amt), 0) AS abs_amt,COALESCE((tbl1.gross / tbl1.day_of_month) * tbl4.unpaid_leave_count, 0) AS lwp_amt, COALESCE(SUM(tbl1.total_payable_sal), 0) AS payable_salary, COALESCE(SUM(tbl1.adv_salary),0) AS advance_amount, COALESCE(SUM(tbl1.loan_adj),0) AS loan_adj, COALESCE(SUM(tbl1.tds),0) AS tds,
                    tbl1.payment_type AS payment_type, COALESCE(SUM(tbl1.stamp), 0) AS stamp, COALESCE(SUM(tbl1.bank_pay), 0) AS bank_pay, COALESCE(SUM(tbl1.cash_pay), 0) AS cash_pay
                    FROM(
                        SELECT he.id AS emp_id, he.name AS emp_name, he.id_card_no AS emp_id_card, he.initial_employment_date AS emp_joining_date, he.department_id AS dept_id, he.job_id AS des_id, he.s_bank_account_no as bank_ac,
                        he.work_location_id AS work_loc_id, hc.wage AS basic, hc.hra AS house_rent, hc.medical_allowance AS medical_alw, hc.travel_allowance AS con_alw,
                        hc.gross_salary AS gross, COALESCE(ast.no_absence + ast.actual_late_count, 0) AS absent_day, ast.no_presence AS present_day, ast.no_of_days AS day_of_month,
                        COALESCE((ast.no_absence + ast.actual_late_count) * ast.per_day_salary, 0) AS ab_amt,
                        SUM(CASE WHEN hpl.code = 'NET' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS total_payable_sal,
                        SUM(CASE WHEN hpl.code = 'SAR' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS adv_salary,
                        SUM(CASE WHEN hpl.code in ('LOANINS', 'LOANINT') THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS loan_adj,
                        SUM(CASE WHEN hpl.code = 'PF' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS pf, hc.tds_deduction AS tds,
                        hp.disbursement_type AS payment_type, hc.stamp_deduction AS stamp, hp.bank_amount AS bank_pay, hp.cash_amount AS cash_pay
                        FROM hr_employee he
                        LEFT JOIN hr_contract hc ON hc.employee_id = he.id
                        LEFT JOIN (SELECT * FROM attendance_sheet WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}') ast ON ast.employee_id = he.id
                        LEFT JOIN hr_payslip hp ON hp.employee_id = he.id
                        LEFT JOIN hr_payslip_line hpl ON hpl.slip_id = hp.id
                        WHERE DATE(hp.date_to) BETWEEN '{0}' AND '{1}' {2} AND hc.state = 'open'
                        {3} {4} {5} {6}
                        GROUP BY he.id, he.name, he.id_card_no, he.initial_employment_date, he.department_id, hp.disbursement_type, hp.cash_amount, hp.bank_amount, hc.stamp_deduction, he.s_bank_account_no, he.job_id, he.work_location_id, hc.wage , hc.hra, hc.medical_allowance, hc.travel_allowance, hc.gross_salary, ast.no_absence, ast.no_presence, ast.no_of_days, hc.tds_deduction, ast.actual_late_count, ast.per_day_salary
                        ) tbl1
                        LEFT JOIN (
                            SELECT ast.employee_id, COUNT(astl.id) AS holy_day
                            FROM attendance_sheet ast
                            LEFT JOIN attendance_sheet_line astl ON astl.att_sheet_id = ast.id
                            WHERE astl.status in ('ph', 'weekend')
                            AND ast.state='done' AND DATE(ast.date_to) BETWEEN '{0}' AND '{1}'
                            GROUP BY ast.employee_id
                        ) tbl2 ON tbl2.employee_id = tbl1.emp_id
                        LEFT JOIN (
                                SELECT leave_tbl.emp_id, COALESCE(SUM(hld.leave_no), 0) AS leave_count
                                FROM (
                                        SELECT hl.id AS leave_id, hl.employee_id AS emp_id
                                        FROM hr_leave hl
                                        JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                                        WHERE hl.state='validate' AND hlt.type_code IN ('CL', 'ML', 'PL') AND DATE(hl.request_date_to) BETWEEN '{0}' AND '{1}'
                                        GROUP BY hl.id, hl.employee_id
                                    ) leave_tbl
                                LEFT JOIN hr_leave_details hld ON hld.leave_id = leave_tbl.leave_id
                                GROUP BY leave_tbl.emp_id
                                ORDER BY leave_tbl.emp_id
                        ) tbl3 ON tbl3.emp_id = tbl1.emp_id
                        LEFT JOIN (
                                SELECT leave_tbl.emp_id, COALESCE(SUM(hld.leave_no), 0) AS unpaid_leave_count
                                FROM (
                                        SELECT hl.id AS unpaid_leave_days, hl.employee_id AS emp_id
                                        FROM hr_leave hl
                                        JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                                        WHERE hl.state='validate' AND hlt.type_code = 'LWP'
                                        AND DATE(hl.request_date_to) BETWEEN '{0}' AND '{1}'
                                        GROUP BY hl.id, hl.employee_id
                                    ) leave_tbl
                                LEFT JOIN hr_leave_details hld ON hld.leave_id = leave_tbl.unpaid_leave_days
                                WHERE DATE(hld.leave_date) BETWEEN '{0}' AND '{1}'
                                GROUP BY leave_tbl.emp_id
                                ORDER BY leave_tbl.emp_id
                        ) tbl4 ON tbl4.emp_id = tbl1.emp_id
                    LEFT JOIN hr_department hd ON hd.id = tbl1.dept_id
                    LEFT JOIN hr_job hj ON hj.id = tbl1.des_id
                    LEFT JOIN stock_location sl ON sl.id = tbl1.work_loc_id
                    GROUP BY tbl1.emp_id, tbl1.emp_name, tbl1.payment_type, tbl1.emp_id_card, tbl1.emp_joining_date, hd.name, hj.name, sl.name, tbl1.work_loc_id, tbl1.bank_ac,tbl1.gross,tbl1.day_of_month,tbl4.unpaid_leave_count
                    ORDER BY tbl1.emp_id_card, tbl1.emp_name
                    """.format(start_date, end_date, state_filter, dept_filter2, work_loc_filter, include_non_zero_payable_filter, report_type_filter)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        # data_list = []

        # for d in data_res:
        #     vals = {
        #         'id_card_no': d['emp_id_card'],
        #         'employee_name': d['emp_name'],
        #         'joining_date': d['emp_joining_date'],
        #         'dept_name': d['dept_name'],
        #         'emp_designation': d['emp_designation'],
        #         'bnk_ac': d['bank_ac'],
        #         'work_loc_id': d['work_loc_id'],
        #         'emp_work_location': d['emp_work_location'],
        #         'basic_salary': d['basic'],
        #         'house_rent': d['house_rent'],
        #         'medical_alw': d['medical_alw'],
        #         'con_alw': d['con_alw'],
        #         'gross_salary': d['gross'],
        #         'holy_day': d['holy_day'],
        #         'leave': d['no_of_leave'],
        #         'abs_day': d['absent_day'],
        #         'present_day': d['present_day'],
        #         'total_day_of_month': d['day_of_month'],
        #         'abs_amt': d['ab_amt'],
        #         'payable_salary': d['total_payable_sal'],
        #         'tds': d['tds'],
        #         'advance_amount': d['adv_salary'],
        #         'loan_adj': d['loan'],
        #         'pf': d['tpf'],
        #         'stamp': d['stamp'],
        #         'cash_pay': d['cash_pay'],
        #         'bank_pay': d['bank_pay'],
        #     }
        #     data_list.append(vals)

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
                            SELECT COALESCE(COUNT(tbl1.emp_id), 0) AS total_emp, COALESCE(tbl1.work_loc_id, 100000) AS work_loc_id, sl.name AS emp_work_location, COALESCE(SUM(tbl1.basic), 0) AS basic_salary, COALESCE(SUM(tbl1.house_rent), 0) AS house_rent,
                            COALESCE(SUM(tbl1.medical_alw), 0) AS medical_alw, COALESCE(SUM(tbl1.con_alw), 0) AS con_alw, COALESCE(SUM(tbl1.gross), 0) AS gross_salary, COALESCE(SUM(tbl2.holy_day), 0) AS holy_day, COALESCE(SUM(tbl1.pf), 0) AS pf,
                            COALESCE(SUM(tbl3.leave_count), 0) AS leave, COALESCE(SUM(tbl1.absent_day), 0) AS abs_day, COALESCE(SUM(tbl1.present_day),0) AS present_day, COALESCE(SUM(tbl1.day_of_month),0) AS total_day_of_month,
                            COALESCE(SUM(tbl1.ab_amt), 0) AS abs_amt, COALESCE(SUM(tbl1.total_payable_sal), 0) AS payable_salary, COALESCE(SUM(tbl1.adv_salary),0) AS advance_amount, COALESCE(SUM(tbl1.loan_adj),0) AS loan_adj, COALESCE(SUM(tbl1.tds),0) AS tds,
                            COALESCE(SUM(tbl1.stamp), 0) AS stamp, COALESCE(SUM(tbl1.bank_pay), 0) AS bank_pay, COALESCE(SUM(tbl1.cash_pay), 0) AS cash_pay
                            FROM(
                                SELECT he.id AS emp_id, he.work_location_id AS work_loc_id, hc.wage AS basic, hc.hra AS house_rent, hc.medical_allowance AS medical_alw, hc.travel_allowance AS con_alw,
                                hc.gross_salary AS gross, COALESCE(ast.no_absence + ast.actual_late_count, 0) AS absent_day, ast.no_presence AS present_day, ast.no_of_days AS day_of_month, he.department_id AS dept_id,
                                COALESCE((ast.no_absence + ast.actual_late_count) * ast.per_day_salary, 0) AS ab_amt,
                                SUM(CASE WHEN hpl.code = 'NET' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS total_payable_sal,
                                SUM(CASE WHEN hpl.code = 'SAR' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS adv_salary,
                                SUM(CASE WHEN hpl.code in ('LOANINS', 'LOANINT') THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS loan_adj,
                                SUM(CASE WHEN hpl.code = 'PF' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS pf, hc.tds_deduction AS tds, hc.stamp_deduction AS stamp,
                                hp.bank_amount AS bank_pay, hp.cash_amount AS cash_pay
                            -- 	SUM(CASE WHEN hc.disbursement_type = 'cash' THEN (COALESCE(hp.cash_amount, 0) - COALESCE(hc.stamp_deduction, 0)) ELSE 
                            -- 		CASE WHEN hc.disbursement_type = 'bank_cash' THEN (COALESCE((hp.cash_amount/2)::INT, 0) - COALESCE(hc.stamp_deduction, 0)) ELSE 0
                            -- 		END END) AS cash_pay,
                            -- 	SUM(CASE WHEN hc.disbursement_type = 'bank' THEN (COALESCE(hp.bank_amount, 0) - COALESCE(hc.stamp_deduction, 0)) ELSE 
                            -- 		CASE WHEN hc.disbursement_type = 'bank_cash' THEN COALESCE((hp.bank_amount/2)::INT, 0) ELSE 0
                            -- 		END END) AS bank_pay
                                FROM hr_employee he
                                LEFT JOIN hr_contract hc ON hc.employee_id = he.id
                                LEFT JOIN (SELECT * FROM attendance_sheet WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}') ast ON ast.employee_id = he.id
                                LEFT JOIN hr_payslip hp ON hp.employee_id = he.id
                                LEFT JOIN hr_payslip_line hpl ON hpl.slip_id = hp.id
                                WHERE DATE(hp.date_to) BETWEEN '{0}' AND '{1}' {2} AND hc.state = 'open'
                                {4} {5} {6}
                                GROUP BY he.id, hp.cash_amount, hp.bank_amount, hc.stamp_deduction, he.work_location_id, hc.wage , hc.hra, hc.medical_allowance, hc.travel_allowance, hc.gross_salary, ast.no_absence, ast.no_presence, ast.no_of_days, hc.tds_deduction, ast.actual_late_count, ast.per_day_salary
                                ) tbl1
                            LEFT JOIN (
                                SELECT ast.employee_id, COUNT(astl.id) AS holy_day
                                FROM attendance_sheet ast
                                LEFT JOIN attendance_sheet_line astl ON astl.att_sheet_id = ast.id
                                WHERE astl.status in ('ph', 'weekend')
                                AND ast.state='done' AND DATE(ast.date_to) BETWEEN '{0}' AND '{1}'
                                GROUP BY ast.employee_id
                            ) tbl2 ON tbl2.employee_id = tbl1.emp_id
                                LEFT JOIN (
                                    SELECT leave_tbl.emp_id, COALESCE(SUM(hld.leave_no), 0) AS leave_count
                                    FROM (
                                            SELECT hl.id AS leave_id, hl.employee_id AS emp_id
                                            FROM hr_leave hl
                                            WHERE hl.state='validate'
                                            AND DATE(hl.request_date_to) BETWEEN '{0}' AND '{1}'
                                            GROUP BY hl.id, hl.employee_id
                                        ) leave_tbl
                                    LEFT JOIN hr_leave_details hld ON hld.leave_id = leave_tbl.leave_id
                                    WHERE DATE(hld.leave_date) BETWEEN '{0}' AND '{1}'
                                    GROUP BY leave_tbl.emp_id
                                    ORDER BY leave_tbl.emp_id
                            ) tbl3 ON tbl3.emp_id = tbl1.emp_id
                            LEFT JOIN stock_location sl ON sl.id = tbl1.work_loc_id
                            {3}
                            GROUP BY sl.name, tbl1.work_loc_id
                            ORDER BY sl.name
                            """.format(start_date, end_date, state_filter, dept_filter, work_loc_filter, include_non_zero_payable_filter, report_type_filter)
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
            'state_name': state_name,
        }
        return data
