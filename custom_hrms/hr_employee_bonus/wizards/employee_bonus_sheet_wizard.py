from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import datetime
from datetime import datetime
from itertools import groupby

import xlsxwriter

import base64
from io import BytesIO


class EmployeeBonusSheetReportWizard(models.TransientModel):
    _name = "employee.bonus.sheet.report.wizard"
    _description = "Employee Bonus Sheet Wizard"

    file_data = fields.Binary('Employee Bonus Sheet Report')
    report_type = fields.Selection([
        ('01', 'Bonus Type wise'),
        ('02', 'All'),
    ], string='Report Type', required=True, default='01')
    start_date = fields.Date(string='From Date', required=True)
    end_date = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    dept_id = fields.Many2one('hr.department', string='Department')
    bonus_type_id = fields.Many2one('hr.employee.bonus.type', string='Bonus Type')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed'),
                              ('paid', 'Payslip Done')], default='confirmed')

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('Start date cannot be greater than the end date.'))

    def employee_bonus_sheet_report_pdf(self):
        start_date = self.start_date
        end_date = self.end_date
        user_work_location_id = self.user_work_location_id
        dept_id = self.dept_id
        bonus_type_id = self.bonus_type_id
        state = self.state

        # get data from sql
        data = self.employee_bonus_sheet_report_sql(start_date, end_date, user_work_location_id, dept_id, bonus_type_id,
                                                    state)

        return self.env.ref('hr_employee_bonus.employee_bonus_sheet_tmpl').with_context(landscape=True).report_action(
            self, data=data)

    def employee_bonus_sheet_report_excel(self):
        start_date = self.start_date
        end_date = self.end_date
        user_work_location_id = self.user_work_location_id
        dept_id = self.dept_id
        bonus_type_id = self.bonus_type_id
        state = self.state

        # get data from sql
        data = self.employee_bonus_sheet_report_sql(start_date, end_date, user_work_location_id, dept_id, bonus_type_id,
                                                    state)

        start_date = datetime.strptime(str(start_date), '%Y-%m-%d').strftime('%d-%b-%Y')
        end_date = datetime.strptime(str(end_date), '%Y-%m-%d').strftime('%d-%b-%Y')

        file_name = "Employee Bonus Sheet Report (%s - %s).xlsx" % (start_date, end_date)
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
        grand_total_basic = 0
        grand_total_house_rent = 0
        grand_total_medical_alw = 0
        grand_total_con_alw = 0
        grand_total_gross_salary = 0
        grand_total_bonus_amount = 0
        grand_total_stamp = 0
        grand_total_cash_amt = 0
        grand_total_bank_amt = 0

        if not data['form']['user_work_location_id']:
            summary_sheet = workbook.add_worksheet('Branch Summary')

            summary_sheet.merge_range(0, 0, 0, 10, "{0}".format(data['form']['company_id'][1]), format0)
            summary_sheet.merge_range(1, 0, 2, 10, 'Bonus Sheet', format0)

            summary_sheet.write(3, 0, 'Branch', format1)
            summary_sheet.write(3, 1, 'Total Employee', format1)
            summary_sheet.write(3, 2, 'Basic', format1)
            summary_sheet.write(3, 3, 'House Rent', format2)
            summary_sheet.write(3, 4, 'Medical', format2)
            summary_sheet.write(3, 5, 'Con. Allowance', format2)
            summary_sheet.write(3, 6, 'Gross Salary', format2)
            summary_sheet.write(3, 7, 'Bonus Amount', format1)
            summary_sheet.write(3, 8, 'Stamp', format1)
            summary_sheet.write(3, 9, 'Cash Amount', format1)
            summary_sheet.write(3, 10, 'Bank Amount', format1)

            summary_total_emp = 0
            summary_total_basic = 0
            summary_total_house_rent = 0
            summary_total_medical_alw = 0
            summary_total_con_alw = 0
            summary_total_gross_salary = 0
            summary_total_bonus_amount = 0
            summary_total_stamp = 0
            summary_total_cash_amt = 0
            summary_total_bank_amt = 0

            summary_row = 4
            summary_col = 0

            for line in data['summary_data_list']:
                summary_sheet.write(summary_row, summary_col, line['loc_name'], format4)
                summary_sheet.write(summary_row, summary_col + 1, line['total_emp'], format5)
                summary_total_emp = summary_total_emp + line['total_emp']
                summary_sheet.write(summary_row, summary_col + 2, line['basic'], format6)
                summary_total_basic = summary_total_basic + line['basic']
                summary_sheet.write(summary_row, summary_col + 3, line['house_rent'], format6)
                summary_total_house_rent = summary_total_house_rent + line['house_rent']
                summary_sheet.write(summary_row, summary_col + 4, line['medical_alw'], format6)
                summary_total_medical_alw = summary_total_medical_alw + line['medical_alw']
                summary_sheet.write(summary_row, summary_col + 5, line['con_alw'], format6)
                summary_total_con_alw = summary_total_con_alw + line['con_alw']
                summary_sheet.write(summary_row, summary_col + 6, line['gross_salary'], format6)
                summary_total_gross_salary = summary_total_gross_salary + line['gross_salary']
                summary_sheet.write(summary_row, summary_col + 7, line['bonus_amount'], format6)
                summary_total_bonus_amount = summary_total_bonus_amount + line['bonus_amount']
                summary_sheet.write(summary_row, summary_col + 8, line['stamp'], format6)
                summary_total_stamp = summary_total_stamp + line['stamp']
                summary_sheet.write(summary_row, summary_col + 9, line['cash_amt'], format6)
                summary_total_cash_amt = summary_total_cash_amt + line['cash_amt']
                summary_sheet.write(summary_row, summary_col + 10, line['bank_amt'], format6)
                summary_total_bank_amt = summary_total_bank_amt + line['bank_amt']

                summary_row = summary_row + 1

            summary_final_row = summary_row
            summary_final_col = 0
            summary_sheet.write(summary_final_row, summary_final_col, 'Total', format7)
            summary_sheet.write(summary_final_row, summary_final_col + 1, summary_total_emp, format9)
            summary_sheet.write(summary_final_row, summary_final_col + 2, summary_total_basic, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 3, summary_total_house_rent, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 4, summary_total_medical_alw, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 5, summary_total_con_alw, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 6, summary_total_gross_salary, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 7, summary_total_bonus_amount, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 8, summary_total_stamp, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 9, summary_total_cash_amt, format7)
            summary_sheet.write(summary_final_row, summary_final_col + 10, summary_total_bank_amt, format7)

        for line in data['csr']:
            for line2 in line:
                sheet = workbook.add_worksheet(line[line2][0]['loc_name'])

                if data['form']['report_type'] == '01':
                    if data['calc_type'] != 'percentage':
                        sheet.merge_range(0, 0, 0, 16, "{0}".format(data['form']['company_id'][1]), format0)
                        sheet.merge_range(1, 0, 2, 16, "Bonus Sheet\nFor the %s - %s" % (
                            data['form']['bonus_type_id'][1],
                            datetime.strptime(str(data['form']['start_date']), '%Y-%m-%d').strftime('%Y')), format0)
                        sheet.merge_range(3, 0, 3, 6, 'Employee Information', format2)
                        sheet.merge_range(3, 7, 3, 11, 'Salary Information', format2)
                        sheet.merge_range(3, 12, 4, 12, 'Bonus Amount', format3)
                        sheet.merge_range(3, 13, 4, 13, 'Stamp', format2)
                        sheet.merge_range(3, 14, 4, 14, 'Cash Amount', format3)
                        sheet.merge_range(3, 15, 4, 15, 'Bank Amount', format3)
                        sheet.merge_range(3, 16, 4, 16, 'Signature', format2)
                    else:
                        sheet.merge_range(0, 0, 0, 17, "{0}".format(data['form']['company_id'][1]), format0)
                        sheet.merge_range(1, 0, 2, 17, "Bonus Sheet\nFor the %s - %s" % (
                            data['form']['bonus_type_id'][1],
                            datetime.strptime(str(data['form']['start_date']), '%Y-%m-%d').strftime('%Y')), format0)
                        sheet.merge_range(3, 0, 3, 6, 'Employee Information', format2)
                        sheet.merge_range(3, 7, 3, 11, 'Salary Information', format2)
                        sheet.merge_range(3, 12, 4, 12, 'Bonus Percentage', format3)
                        sheet.merge_range(3, 13, 4, 13, 'Bonus Amount', format3)
                        sheet.merge_range(3, 14, 4, 14, 'Stamp', format2)
                        sheet.merge_range(3, 15, 4, 15, 'Cash Amount', format3)
                        sheet.merge_range(3, 16, 4, 16, 'Bank Amount', format3)
                        sheet.merge_range(3, 17, 4, 17, 'Signature', format2)

                    sheet.write(4, 0, 'Employee ID', format1)
                    sheet.write(4, 1, 'Employee', format1)
                    sheet.write(4, 2, 'Joining Date', format1)
                    sheet.write(4, 3, 'Designation', format1)
                    sheet.write(4, 4, 'Work Location', format1)
                    sheet.write(4, 5, 'Department', format1)
                    sheet.write(4, 6, 'Bonus Date', format1)
                    sheet.write(4, 7, 'Basic', format3)
                    sheet.write(4, 8, 'House Rent', format3)
                    sheet.write(4, 9, 'Medical', format3)
                    sheet.write(4, 10, 'Con. Allowance', format3)
                    sheet.write(4, 11, 'Gross Salary', format3)

                    row = 5
                    col = 0

                    total_basic = 0
                    total_house_rent = 0
                    total_medical_alw = 0
                    total_con_alw = 0
                    total_gross_salary = 0
                    total_bonus_amount = 0
                    total_stamp = 0
                    total_cash_amt = 0
                    total_bank_amt = 0

                    for line3 in line[line2]:
                        if data['calc_type'] != 'percentage':
                            sheet.write(row, col, line3['old_emp_id'], format4)
                            sheet.write(row, col + 1, line3['emp_name'], format4)
                            joining_date = datetime.strptime(str(line3['joining_date']), '%Y-%m-%d').strftime(
                                '%d-%b-%Y') if \
                                line3['joining_date'] else None
                            sheet.write(row, col + 2, joining_date, format4)
                            sheet.write(row, col + 3, line3['job_name'], format4)
                            sheet.write(row, col + 4, line3['loc_name'], format4)
                            sheet.write(row, col + 5, line3['dept_name'], format4)
                            sheet.write(row, col + 6,
                                        datetime.strptime(str(line3['bonus_date']), '%Y-%m-%d').strftime('%d-%b-%Y'),
                                        format4)
                            sheet.write(row, col + 7, round(line3['basic'], 2), format6)
                            total_basic = total_basic + line3['basic']
                            grand_total_basic = grand_total_basic + line3['basic']
                            sheet.write(row, col + 8, round(line3['house_rent'], 2), format6)
                            total_house_rent = total_house_rent + line3['house_rent']
                            grand_total_house_rent = grand_total_house_rent + line3['house_rent']
                            sheet.write(row, col + 9, round(line3['medical_alw'], 2), format6)
                            total_medical_alw = total_medical_alw + line3['medical_alw']
                            grand_total_medical_alw = grand_total_medical_alw + line3['medical_alw']
                            sheet.write(row, col + 10, round(line3['con_alw'], 2), format6)
                            total_con_alw = total_con_alw + line3['con_alw']
                            grand_total_con_alw = grand_total_con_alw + line3['con_alw']
                            sheet.write(row, col + 11, round(line3['gross_salary'], 2), format6)
                            total_gross_salary = total_gross_salary + line3['gross_salary']
                            grand_total_gross_salary = grand_total_gross_salary + line3['gross_salary']
                            sheet.write(row, col + 12, round(line3['bonus_amount'], 2), format6)
                            total_bonus_amount = total_bonus_amount + line3['bonus_amount']
                            grand_total_bonus_amount = grand_total_bonus_amount + line3['bonus_amount']
                            sheet.write(row, col + 13, round(line3['stamp'], 2), format6)
                            total_stamp = total_stamp + line3['stamp']
                            grand_total_stamp = grand_total_stamp + line3['stamp']
                            if line3['disbursement_type'] in ('cash', 'bank_cash'):
                                cash_amt = line3['cash_amt'] - line3['stamp']
                            else:
                                cash_amt = line3['cash_amt']
                            sheet.write(row, col + 14, round(cash_amt, 2), format6)
                            total_cash_amt = total_cash_amt + cash_amt
                            grand_total_cash_amt = grand_total_cash_amt + cash_amt
                            if line3['disbursement_type'] == 'bank':
                                bank_amt = line3['bank_amt'] - line3['stamp']
                            else:
                                bank_amt = line3['bank_amt']
                            sheet.write(row, col + 15, round(bank_amt, 2), format6)
                            total_bank_amt = total_bank_amt + bank_amt
                            grand_total_bank_amt = grand_total_bank_amt + bank_amt
                            sheet.write(row, col + 16, None, format5)

                            row = row + 1
                            total_emp = total_emp + 1

                            final_row = row
                            final_col = 0

                            sheet.merge_range(final_row, final_col, final_row, final_col + 6, 'TOTAL', format7)
                            sheet.write(final_row, final_col + 7, total_basic, format7)
                            sheet.write(final_row, final_col + 8, total_house_rent, format7)
                            sheet.write(final_row, final_col + 9, total_medical_alw, format7)
                            sheet.write(final_row, final_col + 10, total_con_alw, format7)
                            sheet.write(final_row, final_col + 11, total_gross_salary, format7)
                            sheet.write(final_row, final_col + 12, total_bonus_amount, format7)
                            sheet.write(final_row, final_col + 13, total_stamp, format7)
                            sheet.write(final_row, final_col + 14, total_cash_amt, format7)
                            sheet.write(final_row, final_col + 15, total_bank_amt, format7)
                            sheet.write(final_row, final_col + 16, None, format7)

                        else:
                            sheet.write(row, col, line3['old_emp_id'], format4)
                            sheet.write(row, col + 1, line3['emp_name'], format4)
                            joining_date = datetime.strptime(str(line3['joining_date']), '%Y-%m-%d').strftime(
                                '%d-%b-%Y') if \
                                line3['joining_date'] else None
                            sheet.write(row, col + 2, joining_date, format4)
                            sheet.write(row, col + 3, line3['job_name'], format4)
                            sheet.write(row, col + 4, line3['loc_name'], format4)
                            sheet.write(row, col + 5, line3['dept_name'], format4)
                            sheet.write(row, col + 6,
                                        datetime.strptime(str(line3['bonus_date']), '%Y-%m-%d').strftime('%d-%b-%Y'),
                                        format4)
                            sheet.write(row, col + 7, round(line3['basic'], 2), format6)
                            total_basic = total_basic + line3['basic']
                            grand_total_basic = grand_total_basic + line3['basic']
                            sheet.write(row, col + 8, round(line3['house_rent'], 2), format6)
                            total_house_rent = total_house_rent + line3['house_rent']
                            grand_total_house_rent = grand_total_house_rent + line3['house_rent']
                            sheet.write(row, col + 9, round(line3['medical_alw'], 2), format6)
                            total_medical_alw = total_medical_alw + line3['medical_alw']
                            grand_total_medical_alw = grand_total_medical_alw + line3['medical_alw']
                            sheet.write(row, col + 10, round(line3['con_alw'], 2), format6)
                            total_con_alw = total_con_alw + line3['con_alw']
                            grand_total_con_alw = grand_total_con_alw + line3['con_alw']
                            sheet.write(row, col + 11, round(line3['gross_salary'], 2), format6)
                            total_gross_salary = total_gross_salary + line3['gross_salary']
                            grand_total_gross_salary = grand_total_gross_salary + line3['gross_salary']
                            sheet.write(row, col + 12, '{0}%'.format(line3['percent']), format6)
                            sheet.write(row, col + 13, round(line3['bonus_amount'], 2), format6)
                            total_bonus_amount = total_bonus_amount + line3['bonus_amount']
                            grand_total_bonus_amount = grand_total_bonus_amount + line3['bonus_amount']
                            sheet.write(row, col + 14, round(line3['stamp'], 2), format6)
                            total_stamp = total_stamp + line3['stamp']
                            grand_total_stamp = grand_total_stamp + line3['stamp']
                            if line3['disbursement_type'] in ('cash', 'bank_cash'):
                                cash_amt = line3['cash_amt'] - line3['stamp']
                            else:
                                cash_amt = line3['cash_amt']
                            sheet.write(row, col + 15, round(cash_amt, 2), format6)
                            total_cash_amt = total_cash_amt + cash_amt
                            grand_total_cash_amt = grand_total_cash_amt + cash_amt
                            if line3['disbursement_type'] == 'bank':
                                bank_amt = line3['bank_amt'] - line3['stamp']
                            else:
                                bank_amt = line3['bank_amt']
                            sheet.write(row, col + 16, round(bank_amt, 2), format6)
                            total_bank_amt = total_bank_amt + bank_amt
                            grand_total_bank_amt = grand_total_bank_amt + bank_amt
                            sheet.write(row, col + 17, None, format5)

                            row = row + 1
                            total_emp = total_emp + 1

                        final_row = row
                        final_col = 0

                        sheet.merge_range(final_row, final_col, final_row, final_col + 6, 'TOTAL', format7)
                        sheet.write(final_row, final_col + 7, total_basic, format7)
                        sheet.write(final_row, final_col + 8, total_house_rent, format7)
                        sheet.write(final_row, final_col + 9, total_medical_alw, format7)
                        sheet.write(final_row, final_col + 10, total_con_alw, format7)
                        sheet.write(final_row, final_col + 11, total_gross_salary, format7)
                        sheet.write(final_row, final_col + 12, None, format7)
                        sheet.write(final_row, final_col + 13, total_bonus_amount, format7)
                        sheet.write(final_row, final_col + 14, total_stamp, format7)
                        sheet.write(final_row, final_col + 15, total_cash_amt, format7)
                        sheet.write(final_row, final_col + 16, total_bank_amt, format7)
                        sheet.write(final_row, final_col + 17, None, format7)

                else:
                    sheet.merge_range(0, 0, 0, 17, "{0}".format(data['form']['company_id'][1]), format0)
                    sheet.merge_range(1, 0, 2, 17, "Bonus Sheet For The Year %s" % (
                        datetime.strptime(str(data['form']['start_date']), '%Y-%m-%d').strftime('%Y')), format0)

                    sheet.merge_range(3, 0, 3, 6, 'Employee Information', format2)
                    sheet.merge_range(3, 7, 3, 11, 'Salary Information', format2)
                    sheet.merge_range(3, 12, 4, 12, 'Bonus Type', format3)
                    sheet.merge_range(3, 13, 4, 13, 'Bonus Amount', format3)
                    sheet.merge_range(3, 14, 4, 14, 'Stamp', format3)
                    sheet.merge_range(3, 15, 4, 15, 'Cash Amount', format3)
                    sheet.merge_range(3, 16, 4, 16, 'Bank Amount', format3)
                    sheet.merge_range(3, 17, 4, 17, 'Signature', format2)

                    sheet.write(4, 0, 'Employee ID', format1)
                    sheet.write(4, 1, 'Employee', format1)
                    sheet.write(4, 2, 'Joining Date', format1)
                    sheet.write(4, 3, 'Designation', format1)
                    sheet.write(4, 4, 'Work Location', format1)
                    sheet.write(4, 5, 'Department', format1)
                    sheet.write(4, 6, 'Bonus Date', format1)
                    sheet.write(4, 7, 'Basic', format3)
                    sheet.write(4, 8, 'House Rent', format3)
                    sheet.write(4, 9, 'Medical', format3)
                    sheet.write(4, 10, 'Con. Allowance', format3)
                    sheet.write(4, 11, 'Gross Salary', format3)

                    row = 5
                    col = 0

                    total_basic = 0
                    total_house_rent = 0
                    total_medical_alw = 0
                    total_con_alw = 0
                    total_gross_salary = 0
                    total_bonus_amount = 0
                    total_stamp = 0
                    total_cash_amt = 0
                    total_bank_amt = 0

                    for line3 in line[line2]:
                        sheet.write(row, col, line3['old_emp_id'], format4)
                        sheet.write(row, col + 1, line3['emp_name'], format4)
                        sheet.write(row, col + 2,
                                    datetime.strptime(str(line3['joining_date']), '%Y-%m-%d').strftime('%d-%b-%Y'),
                                    format4)
                        sheet.write(row, col + 3, line3['job_name'], format4)
                        sheet.write(row, col + 4, line3['loc_name'], format4)
                        sheet.write(row, col + 5, line3['dept_name'], format4)
                        sheet.write(row, col + 6,
                                    datetime.strptime(str(line3['bonus_date']), '%Y-%m-%d').strftime('%d-%b-%Y'),
                                    format6)
                        sheet.write(row, col + 7, round(line3['basic'], 2), format6)
                        total_basic = total_basic + line3['basic']
                        grand_total_basic = grand_total_basic + line3['basic']
                        sheet.write(row, col + 8, round(line3['house_rent'], 2), format6)
                        total_house_rent = total_house_rent + line3['house_rent']
                        grand_total_house_rent = grand_total_house_rent + line3['house_rent']
                        sheet.write(row, col + 9, round(line3['medical_alw'], 2), format6)
                        total_medical_alw = total_medical_alw + line3['medical_alw']
                        grand_total_medical_alw = grand_total_medical_alw + line3['medical_alw']
                        sheet.write(row, col + 10, round(line3['con_alw'], 2), format6)
                        total_con_alw = total_con_alw + line3['con_alw']
                        grand_total_con_alw = grand_total_con_alw + line3['con_alw']
                        sheet.write(row, col + 11, round(line3['gross_salary'], 2), format6)
                        total_gross_salary = total_gross_salary + line3['gross_salary']
                        grand_total_gross_salary = grand_total_gross_salary + line3['gross_salary']
                        sheet.write(row, col + 12, line3['bonus_type_name'], format6)
                        sheet.write(row, col + 13, round(line3['bonus_amount'], 2), format6)
                        total_bonus_amount = total_bonus_amount + line3['bonus_amount']
                        grand_total_bonus_amount = grand_total_bonus_amount + line3['bonus_amount']
                        sheet.write(row, col + 14, round(line3['stamp'], 2), format6)
                        total_stamp = total_stamp + line3['stamp']
                        grand_total_stamp = grand_total_stamp + line3['stamp']
                        if line3['disbursement_type'] in ('cash', 'bank_cash'):
                            cash_amt = line3['cash_amt'] - line3['stamp']
                        else:
                            cash_amt = line3['cash_amt']
                        sheet.write(row, col + 15, round(cash_amt, 2), format6)
                        total_cash_amt = total_cash_amt + cash_amt
                        grand_total_cash_amt = grand_total_cash_amt + cash_amt
                        if line3['disbursement_type'] == 'bank':
                            bank_amt = line3['bank_amt'] - line3['stamp']
                        else:
                            bank_amt = line3['bank_amt']
                        sheet.write(row, col + 16, round(bank_amt, 2), format6)
                        total_bank_amt = total_bank_amt + bank_amt
                        grand_total_bank_amt = grand_total_bank_amt + bank_amt
                        sheet.write(row, col + 17, None, format5)

                        row = row + 1

                    final_row = row
                    final_col = 0

                    sheet.merge_range(final_row, final_col, final_row, final_col + 6, 'TOTAL', format7)
                    sheet.write(final_row, final_col + 7, total_basic, format7)
                    sheet.write(final_row, final_col + 8, total_house_rent, format7)
                    sheet.write(final_row, final_col + 9, total_medical_alw, format7)
                    sheet.write(final_row, final_col + 10, total_con_alw, format7)
                    sheet.write(final_row, final_col + 11, total_gross_salary, format7)
                    sheet.write(final_row, final_col + 12, None, format7)
                    sheet.write(final_row, final_col + 13, total_bonus_amount, format7)
                    sheet.write(final_row, final_col + 14, total_stamp, format7)
                    sheet.write(final_row, final_col + 15, total_cash_amt, format7)
                    sheet.write(final_row, final_col + 16, total_bank_amt, format7)
                    sheet.write(final_row, final_col + 17, None, format7)

        sheet = workbook.add_worksheet('Grand Total')

        sheet.merge_range(0, 0, 0, 9, 'GRAND TOTAL', format9)
        sheet.write(1, 0, 'Total Employee', format7)
        sheet.write(1, 1, 'Basic', format7)
        sheet.write(1, 2, 'House Rent', format7)
        sheet.write(1, 3, 'Medical', format7)
        sheet.write(1, 4, 'Con. Allowance', format7)
        sheet.write(1, 5, 'Gross Salary', format7)
        sheet.write(1, 6, 'Bonus Amount', format7)
        sheet.write(1, 7, 'Stamp', format7)
        sheet.write(1, 8, 'Cash Amount', format7)
        sheet.write(1, 9, 'Bank Amount', format7)

        sheet.write(2, 0, total_emp, format9)
        sheet.write(2, 1, grand_total_basic, format7)
        sheet.write(2, 2, grand_total_house_rent, format7)
        sheet.write(2, 3, grand_total_medical_alw, format7)
        sheet.write(2, 4, grand_total_con_alw, format7)
        sheet.write(2, 5, grand_total_gross_salary, format7)
        sheet.write(2, 6, grand_total_bonus_amount, format7)
        sheet.write(2, 7, grand_total_stamp, format7)
        sheet.write(2, 8, grand_total_cash_amt, format7)
        sheet.write(2, 9, grand_total_bank_amt, format7)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Bonus Sheet Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.bonus.sheet.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_bonus_sheet_report_sql(self, start_date, end_date, user_work_location_id, dept_id, bonus_type_id, state):
        work_location_filter = ""
        dept_filter = ""
        bonus_type_filter = ""
        dept_name = "All"
        work_location_name = "All"
        bonus_type_name = "All"

        calc_type = self.bonus_type_id.calculation_type

        state_name = dict(self._fields['state'].selection).get(self.state)

        if user_work_location_id:
            work_location_filter = "AND hre.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if dept_id:
            dept_filter = "AND hre.department_id = %s" % dept_id.id
            dept_name = dept_id.display_name

        if bonus_type_id:
            bonus_type_filter = "AND heb.bonus_type_id = %s" % bonus_type_id.id
            bonus_type_name = bonus_type_id.display_name

        data_sql = """
                    SELECT main_tbl.old_emp_id, main_tbl.emp_name, main_tbl.joining_date, main_tbl.bonus_date, main_tbl.disbursement_type, COALESCE(main_tbl.user_work_location_id, 10000) AS user_work_location_id, main_tbl.loc_name, main_tbl.dept_name, main_tbl.job_name, main_tbl.gross_salary, ebt.name AS bonus_type_name, COALESCE(SUM(main_tbl.percent), 0) AS percent, COALESCE(SUM(main_tbl.bonus_amount), 0) AS bonus_amount, COALESCE(main_tbl.stamp, 0) AS stamp, COALESCE(SUM(main_tbl.cash_amt), 0) AS cash_amt, COALESCE(SUM(main_tbl.bank_amt), 0) AS bank_amt,
                    COALESCE(SUM(main_tbl.basic), 0) AS basic, COALESCE(SUM(main_tbl.house_rent), 0) AS house_rent, COALESCE(SUM(main_tbl.medical_alw), 0) AS medical_alw, COALESCE(SUM(main_tbl.con_alw), 0) AS con_alw
                    FROM(
                        SELECT bonus_tbl.old_emp_id, bonus_tbl.emp_name, bonus_tbl.joining_date, bonus_tbl.date AS bonus_date, stl.id AS user_work_location_id, stl.name AS loc_name, hd.name AS dept_name, hj.name AS job_name, bonus_tbl.gross_salary,
                        bonus_tbl.bonus_type_id, bonus_tbl.disbursement_type, bonus_tbl.percent, bonus_tbl.bonus_amount, bonus_tbl.stamp, bonus_tbl.cash_amt, bonus_tbl.bank_amt, bonus_tbl.basic, bonus_tbl.house_rent, bonus_tbl.medical_alw, bonus_tbl.con_alw  
                         FROM (
                            SELECT hre.id_card_no AS old_emp_id, hre.name AS emp_name, hre.initial_employment_date AS joining_date, heb.amount_percentage AS percent, hc.disbursement_type, heb.date, hre.user_work_location_id, hre.department_id, hre.job_id, COALESCE(heb.gross_salary,0) as gross_salary, heb.bonus_type_id, heb.bonus_amount, hc.stamp_deduction AS stamp,
                            SUM(CASE WHEN hc.disbursement_type = 'cash' THEN COALESCE(heb.bonus_amount, 0) ELSE 
                                CASE WHEN hc.disbursement_type = 'bank_cash' THEN COALESCE((heb.bonus_amount/2)::INT, 0) ELSE 0
                                END END) AS cash_amt,
                            SUM(CASE WHEN hc.disbursement_type = 'bank' THEN COALESCE(heb.bonus_amount, 0) ELSE 
                                CASE WHEN hc.disbursement_type = 'bank_cash' THEN COALESCE((heb.bonus_amount/2)::INT, 0) ELSE 0
                                END END) AS bank_amt,
                            hc.wage AS basic, hc.hra AS house_rent, hc.medical_allowance AS medical_alw, hc.travel_allowance AS con_alw
                            FROM hr_employee_bonus heb
                            JOIN hr_employee hre ON hre.id=heb.employee_id
                            JOIN hr_contract hc ON hc.employee_id=hre.id
                            WHERE hc.state='open' AND heb.state='{5}' {2} {3} {4}
                            GROUP BY hre.id_card_no, hre.name, hc.disbursement_type, hre.initial_employment_date, heb.date, heb.amount_percentage, hre.user_work_location_id, hre.department_id, hre.job_id, heb.gross_salary, heb.bonus_type_id, heb.bonus_amount, hc.stamp_deduction,
                            hc.wage, hc.hra, hc.medical_allowance, hc.travel_allowance
                        ) bonus_tbl
                        LEFT JOIN hr_department hd on hd.id = bonus_tbl.department_id
                        LEFT JOIN hr_job hj ON hj.id = bonus_tbl.job_id
                        LEFT JOIN stock_location stl ON stl.id = bonus_tbl.user_work_location_id
                    ) main_tbl
                    JOIN hr_employee_bonus_type ebt ON ebt.id = main_tbl.bonus_type_id
                    WHERE DATE(main_tbl.bonus_date) BETWEEN '{0}' AND '{1}'
                    GROUP BY main_tbl.old_emp_id, main_tbl.emp_name, main_tbl.joining_date, main_tbl.disbursement_type, main_tbl.bonus_date, main_tbl.loc_name, main_tbl.dept_name, main_tbl.job_name, main_tbl.gross_salary, ebt.name, main_tbl.stamp, main_tbl.user_work_location_id
                    ORDER BY main_tbl.old_emp_id, main_tbl.emp_name
                    """.format(start_date, end_date, work_location_filter, dept_filter, bonus_type_filter, state)
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

        summary_data_sql = """
                            SELECT COALESCE(main_tbl.user_work_location_id, 10000) AS user_work_location_id, main_tbl.loc_name, COALESCE(SUM(main_tbl.total_emp), 0) AS total_emp, COALESCE(SUM(main_tbl.gross_salary), 0) AS gross_salary, COALESCE(SUM(main_tbl.bonus_amt), 0) AS bonus_amount, COALESCE(SUM(main_tbl.stamp), 0) AS stamp, COALESCE(SUM(main_tbl.cash_amt), 0) AS cash_amt, COALESCE(SUM(main_tbl.bank_amt), 0) AS bank_amt,
                            COALESCE(SUM(main_tbl.basic), 0) AS basic, COALESCE(SUM(main_tbl.house_rent), 0) AS house_rent, COALESCE(SUM(main_tbl.medical_alw), 0) AS medical_alw, COALESCE(SUM(main_tbl.con_alw), 0) AS con_alw
                            FROM(
                                SELECT bonus_tbl.total_emp AS total_emp, stl.id AS user_work_location_id, stl.name AS loc_name, bonus_tbl.gross_salary,
                                bonus_tbl.bonus_amt, bonus_tbl.stamp, bonus_tbl.cash_amt, bonus_tbl.bank_amt, bonus_tbl.basic, bonus_tbl.house_rent, bonus_tbl.medical_alw, bonus_tbl.con_alw  
                                 FROM (
                                    SELECT hre.user_work_location_id, COUNT(hre.id) AS total_emp, COALESCE(SUM(hc.gross_salary), 0) AS gross_salary, COALESCE(SUM(heb.bonus_amount), 0) AS bonus_amt, COALESCE(SUM(hc.stamp_deduction), 0) AS stamp,
                                    SUM(CASE WHEN hc.disbursement_type = 'cash' THEN (COALESCE(heb.bonus_amount, 0) - COALESCE(hc.stamp_deduction, 0)) ELSE 
                                        CASE WHEN hc.disbursement_type = 'bank_cash' THEN (COALESCE((heb.bonus_amount/2)::INT, 0) - COALESCE(hc.stamp_deduction, 0)) ELSE 0
                                        END END) AS cash_amt,
                                    SUM(CASE WHEN hc.disbursement_type = 'bank' THEN (COALESCE(heb.bonus_amount, 0) - COALESCE(hc.stamp_deduction, 0)) ELSE 
                                        CASE WHEN hc.disbursement_type = 'bank_cash' THEN COALESCE((heb.bonus_amount/2)::INT, 0) ELSE 0
                                        END END) AS bank_amt,
                                    COALESCE(SUM(hc.wage), 0) AS basic, COALESCE(SUM(hc.hra), 0) AS house_rent, COALESCE(SUM(hc.medical_allowance), 0) AS medical_alw, COALESCE(SUM(hc.travel_allowance), 0) AS con_alw
                                    FROM hr_employee_bonus heb
                                    JOIN hr_employee hre ON hre.id=heb.employee_id
                                    JOIN hr_contract hc ON hc.employee_id=hre.id
                                    WHERE hc.state='open' AND heb.state='confirmed' AND DATE(heb.date) BETWEEN '{0}' AND '{1}' AND heb.state='{5}' {2} {3} {4}
                                    GROUP BY hre.user_work_location_id
                                ) bonus_tbl
                                LEFT JOIN stock_location stl ON stl.id = bonus_tbl.user_work_location_id
                            ) main_tbl
                            GROUP BY main_tbl.loc_name, main_tbl.user_work_location_id
                            ORDER BY main_tbl.loc_name
                        """.format(start_date, end_date, work_location_filter, dept_filter, bonus_type_filter, state)
        self.env.cr.execute(summary_data_sql)
        summary_data_list = self.env.cr.dictfetchall()

        data = {
            'model': "employee.bonus.sheet.report.wizard",
            'form': self.read()[0],
            'csr': final_data_list,
            'summary_data_list': summary_data_list,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'state_name': state_name,
            'bonus_type_name': bonus_type_name,
            'calc_type': calc_type
        }

        return data


class BatchBonusSheetReportWizard(models.TransientModel):
    _name = "batch.bonus.sheet.report.wizard"
    _description = "Employee Batch Bonus Sheet Wizard"

    batch_id = fields.Many2one('batch.hr.employee.bonus', string='Batch Bonus', required=True)
    file_data = fields.Binary('Employee Batch Bonus Sheet Report')

    @api.model
    def default_get(self, fields):
        res = super(BatchBonusSheetReportWizard, self).default_get(fields)
        batch_sheet_obj = self.env['batch.hr.employee.bonus'].browse(self.env.context.get('active_id'))
        if batch_sheet_obj:
            res['batch_id'] = batch_sheet_obj.id
        return res

    def batch_bonus_sheet_report_excel(self):
        batch_id = self.batch_id

        file_name = "Employee Bonus- %s.xlsx" % (batch_id.name)
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

        sheet = workbook.add_worksheet()

        sheet.merge_range(0, 2, 0, 10, "Employee Batch Bonus Sheet", format0)
        sheet.merge_range(1, 2, 2, 10, "%s; Bonus Date:%s" % (batch_id.name, batch_id.bonus_date), format0)

        sheet.write(3, 0, 'SL No.', format2)
        sheet.write(3, 1, 'Employee Name', format2)
        sheet.write(3, 2, 'Employee ID', format2)
        sheet.write(3, 3, 'Joining Date', format2)
        sheet.write(3, 4, 'Work Location', format2)
        sheet.write(3, 5, 'Department', format2)
        sheet.write(3, 6, 'Designation', format2)
        sheet.write(3, 7, 'Gross Amount', format2)
        sheet.write(3, 8, 'Basic Amount', format2)
        sheet.write(3, 9, 'Calculation Type', format2)
        sheet.write(3, 10, 'Based On', format2)
        sheet.write(3, 11, 'FixedAmount/Percentage', format2)
        sheet.write(3, 12, 'Bonus Amount', format2)

        row = 4
        col = 0
        sl_no = 1

        for line in batch_id.emp_bonus_ids:
            sheet.write(row, col, sl_no, format5)
            col = col + 1
            sheet.write(row, col, line.employee_id.name, format5)
            col = col + 1
            sheet.write(row, col, line.id_card_no, format5)
            col = col + 1
            sheet.write(row, col, datetime.strptime(str(line.initial_employment_date), '%Y-%m-%d').strftime('%d-%b-%Y'),
                        format5)
            col = col + 1
            sheet.write(row, col, line.user_work_location_id.name, format5)
            col = col + 1
            sheet.write(row, col, line.department_id.name, format5)
            col = col + 1
            sheet.write(row, col, line.job_id.name, format5)
            col = col + 1
            sheet.write(row, col, line.gross_salary, format5)
            col = col + 1
            sheet.write(row, col, line.basic_salary, format5)
            col = col + 1
            sheet.write(row, col, str(line.calculation_type).upper(), format5)
            col = col + 1
            sheet.write(row, col, str(line.based_on_type or line.calculation_type).upper(), format5)
            col = col + 1
            sheet.write(row, col, line.amount_percentage, format5)
            col = col + 1
            sheet.write(row, col, line.bonus_amount, format5)
            col = col + 1
            row = row + 1
            col = 0

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()
        return {
            'name': 'Employee Batch Bonus Sheet Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=batch.bonus.sheet.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }
