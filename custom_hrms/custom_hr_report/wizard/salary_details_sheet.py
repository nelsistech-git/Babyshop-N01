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


class SalaryDetailSheetReportWizard(models.TransientModel):
    _name = "salary.details.sheet.report.wizard"
    _description = "Salary Detail Sheet Report Wizard"

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
    ], string='Payslip Status', required=True)
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
    ], string='Employee Status', default='all')
    disbursement_type = fields.Selection([
        ('bank_cash', 'Bank & Cash'),
        ('bank', 'Bank'),
        ('cash', 'Cash'),
    ], string="Payment Type", default="bank_cash")

    rpt_type = fields.Selection([
        ('all', 'All'),
        ('details', 'Details'),
        ('summary', 'Summary')
    ], string="Report Type", default="all")

    rpt_for = fields.Selection([
        ('all', 'All'),
        ('management', 'Management'),
        ('staff', 'Staff'),
    ], string="Report For", default="all")

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

    def salary_detail_sheet_report_excel(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        state = self.state
        user_work_location_id = self.user_work_location_id
        include_zero_less_payable = self.include_zero_less_payable
        report_type = self.report_type
        employee_id = self.employee_id

        # get data from sql
        data = self.salary_details_sheet_report_sql(month, year, department_id, state, user_work_location_id,
                                                            include_zero_less_payable, report_type, employee_id)

        file_name = "Salary Detail Sheet Report (%s - %s).xlsx" % (data['month'], data['year'])
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

        grand_total_emp = 0
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

        grand_total_dearness_alw = 0
        grand_total_food_alw = 0
        grand_total_mobile_alw = 0
        grand_total_car_alw = 0
        grand_total_lfa_alw = 0
        grand_total_salbonus_alw = 0
        grand_total_tiffin_alw = 0
        grand_total_att_bonus_alw = 0
        grand_total_other_alw = 0
        grand_total_extra_alw = 0
        grand_total_daily_alw = 0
        grand_total_ota_alw = 0
        grand_total_bonus_alw = 0
        grand_total_loan_int_ded = 0
        grand_total_join_res_ded = 0
        grand_total_disp_ded = 0
        grand_total_medical_leave_ded = 0
        grand_total_insur_ded = 0
        grand_total_late_in_ded = 0
        grand_total_early_out_ded = 0

        # ------------------------- Location wise summary
        if not data['form']['user_work_location_id']:
            summary_sheet = workbook.add_worksheet('Branch Summary')

            summary_sheet.merge_range(0, 0, 0, 10, "{0}".format(data['form']['company_id'][1]), format0)
            summary_sheet.merge_range(1, 0, 1, 10, "Summary Salary Sheet (%s - %s)" % (data['start_date'], data['end_date']),
                                  format0)
            summary_sheet.merge_range(2, 0, 2, 10, 'Branch/Work/Job Location: {0}'.format(data['work_loc_name']), format1)
            summary_sheet.merge_range(3, 0, 3, 10, 'Status: {0}'.format(data['state_name']), format1)
            summary_sheet.merge_range(4, 0, 4, 10, 'Department Name: {0}'.format(data['dept_name']), format1)

            #-------------
            r_row = 6
            r_col = 0
            summary_sheet.write(r_row, r_col, 'Branch', format1)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Salary Structure', format1)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Total Employee', format1)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Basic', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'House Rent', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Medical', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Conveyance', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Dearness', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Meal', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Mobile', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Car', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'LFA', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Salary Bonus', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Tiffin Allowances', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Att.Bonus', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Other Allowances', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Extra Allowances', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Daily Allowances', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Overtime', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Bonus', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Gross Salary', format2)

            # -----------------Deduction
            r_col += 1
            summary_sheet.write(r_row, r_col, 'PF', format2)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'TDS', format2)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Salary Advance', format2)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Loan', format2)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Loan Interest', format2)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Stamp Fee', format2)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Absent', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Join/Resign', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'LWP', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Disciplinary', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Medical Deduction', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Insurance', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Late IN', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Early Out', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Net Payable', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Bank Payment', format3)
            r_col += 1
            summary_sheet.write(r_row, r_col, 'Cash Payment', format3)

            #--------------
            summary_total_emp = 0
            summary_total_basic_salary = 0
            summary_total_house_rent = 0
            summary_total_medical_alw = 0
            summary_total_con_alw = 0
            summary_total_gross_salary = 0
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

            summary_total_dearness_alw = 0
            summary_total_food_alw = 0
            summary_total_mobile_alw = 0
            summary_total_car_alw = 0
            summary_total_lfa_alw = 0
            summary_total_salbonus_alw = 0
            summary_total_tiffin_alw = 0
            summary_total_att_bonus_alw = 0
            summary_total_other_alw = 0
            summary_total_extra_alw = 0
            summary_total_daily_alw = 0
            summary_total_ota_alw = 0
            summary_total_bonus_alw = 0
            summary_total_loan_int_ded = 0
            summary_total_join_res_ded = 0
            summary_total_disp_ded = 0
            summary_total_medical_leave_ded = 0
            summary_total_insur_ded = 0
            summary_total_late_in_ded = 0
            summary_total_early_out_ded = 0

            summary_row = r_row+1
            summary_col = 0
            for line in data['summary_data_res']:
                summary_sheet.write(summary_row, summary_col, line['emp_work_location'], format4)
                summary_col += 1
                summary_sheet.write(summary_row, summary_col, line['sal_struct'], format4)

                summary_col += 1
                total_emp = line['total_emp']
                summary_sheet.write(summary_row, summary_col, total_emp, format6)
                summary_total_emp += total_emp

                summary_col += 1
                basic_salary = round(line['basic_salary'], 2)
                summary_sheet.write(summary_row, summary_col, basic_salary, format6)
                summary_total_basic_salary += basic_salary

                summary_col += 1
                house_rent = round(line['house_rent'], 2)
                summary_sheet.write(summary_row, summary_col, house_rent, format6)
                summary_total_house_rent += house_rent

                summary_col += 1
                medical_alw = round(line['medical_alw'], 2)
                summary_sheet.write(summary_row, summary_col, medical_alw, format6)
                summary_total_medical_alw += medical_alw

                summary_col += 1
                con_alw = round(line['con_alw'], 2)
                summary_sheet.write(summary_row, summary_col, con_alw, format6)
                summary_total_con_alw += con_alw

                summary_col += 1
                dearness_alw = round(line['dearness_alw'], 2)
                summary_sheet.write(summary_row, summary_col, dearness_alw, format6)
                summary_total_dearness_alw += dearness_alw

                summary_col += 1
                food_alw = round(line['food_alw'], 2)
                summary_sheet.write(summary_row, summary_col, food_alw, format6)
                summary_total_food_alw += food_alw

                summary_col += 1
                mobile_alw = round(line['mobile_alw'], 2)
                summary_sheet.write(summary_row, summary_col, mobile_alw, format6)
                summary_total_mobile_alw += mobile_alw

                summary_col += 1
                car_alw = round(line['car_alw'], 2)
                summary_sheet.write(summary_row, summary_col, car_alw, format6)
                summary_total_car_alw += car_alw

                summary_col += 1
                lfa_alw = round(line['lfa_alw'], 2)
                summary_sheet.write(summary_row, summary_col, lfa_alw, format6)
                summary_total_lfa_alw += lfa_alw

                summary_col += 1
                salbonus_alw = round(line['salbonus_alw'], 2)
                summary_sheet.write(summary_row, summary_col, salbonus_alw, format6)
                summary_total_salbonus_alw += salbonus_alw

                summary_col += 1
                tiffin_alw = round(line['tiffin_alw'], 2)
                summary_sheet.write(summary_row, summary_col, tiffin_alw, format6)
                summary_total_tiffin_alw += tiffin_alw

                summary_col += 1
                att_bonus_alw = round(line['att_bonus_alw'], 2)
                summary_sheet.write(summary_row, summary_col, att_bonus_alw, format6)
                summary_total_att_bonus_alw += att_bonus_alw

                summary_col += 1
                other_alw = round(line['other_alw'], 2)
                summary_sheet.write(summary_row, summary_col, other_alw, format6)
                summary_total_other_alw += other_alw

                summary_col += 1
                extra_alw = round(line['extra_alw'], 2)
                summary_sheet.write(summary_row, summary_col, extra_alw, format6)
                summary_total_extra_alw += extra_alw

                summary_col += 1
                daily_alw = round(line['daily_alw'], 2)
                summary_sheet.write(summary_row, summary_col, daily_alw, format6)
                summary_total_daily_alw += daily_alw

                summary_col += 1
                ota_alw = round(line['ota_alw'], 2)
                summary_sheet.write(summary_row, summary_col, ota_alw, format6)
                summary_total_ota_alw += ota_alw

                summary_col += 1
                bonus_alw = round(line['bonus_alw'], 2)
                summary_sheet.write(summary_row, summary_col, bonus_alw, format6)
                summary_total_bonus_alw += bonus_alw

                summary_col += 1
                gross_salary = round(line['gross_salary'], 2)
                summary_sheet.write(summary_row, summary_col, gross_salary, format6)
                summary_total_gross_salary += gross_salary

                # ----------- Deduction
                summary_col += 1
                pf_ded = round(line['pf_ded'], 2)
                summary_sheet.write(summary_row, summary_col, pf_ded, format6)
                summary_total_pf += pf_ded

                summary_col += 1
                tds_ded = round(line['tds_ded'], 2)
                summary_sheet.write(summary_row, summary_col, tds_ded, format6)
                summary_total_tds += tds_ded

                summary_col += 1
                adv_sal_ded = round(line['adv_sal_ded'], 2)
                summary_sheet.write(summary_row, summary_col, adv_sal_ded, format6)
                summary_total_advance_amount += adv_sal_ded

                summary_col += 1
                loan_ded = round(line['loan_ded'], 2)
                summary_sheet.write(summary_row, summary_col, loan_ded, format6)
                summary_total_loan_adj += loan_ded

                summary_col += 1
                loan_int_ded = round(line['loan_int_ded'], 2)
                summary_sheet.write(summary_row, summary_col, loan_int_ded, format6)
                summary_total_loan_int_ded += loan_int_ded

                summary_col += 1
                stamp_ded = round(line['stamp_ded'], 2)
                summary_sheet.write(summary_row, summary_col, stamp_ded, format5)
                summary_total_stamp += stamp_ded

                summary_col += 1
                absent_ded = round(line['absent_ded'], 2)
                summary_sheet.write(summary_row, summary_col, absent_ded, format5)
                summary_total_abs_amt += absent_ded

                summary_col += 1
                join_res_ded = round(line['join_res_ded'], 2)
                summary_sheet.write(summary_row, summary_col, join_res_ded, format5)
                summary_total_join_res_ded += join_res_ded

                summary_col += 1
                lwp_ded = round(line['lwp_ded'], 2)
                summary_sheet.write(summary_row, summary_col, lwp_ded, format5)
                summary_total_lwp_amt += lwp_ded

                summary_col += 1
                disp_ded = round(line['disp_ded'], 2)
                summary_sheet.write(summary_row, summary_col, disp_ded, format5)
                summary_total_disp_ded += disp_ded

                summary_col += 1
                medical_leave_ded = round(line['medical_leave_ded'], 2)
                summary_sheet.write(summary_row, summary_col, medical_leave_ded, format5)
                summary_total_medical_leave_ded += medical_leave_ded

                summary_col += 1
                insur_ded = round(line['insur_ded'], 2)
                summary_sheet.write(summary_row, summary_col, insur_ded, format5)
                summary_total_insur_ded += insur_ded

                summary_col += 1
                late_in_ded = round(line['late_in_ded'], 2)
                summary_sheet.write(summary_row, summary_col, late_in_ded, format5)
                summary_total_late_in_ded += late_in_ded

                summary_col += 1
                early_out_ded = round(line['early_out_ded'], 2)
                summary_sheet.write(summary_row, summary_col, early_out_ded, format5)
                summary_total_early_out_ded += early_out_ded

                summary_col += 1
                total_net_sal = round(line['total_net_sal'], 2)
                summary_sheet.write(summary_row, summary_col, total_net_sal, format5)
                summary_total_payable_salary += total_net_sal

                # -------------------
                summary_col += 1
                bank_pay = round(line['bank_pay'], 2)
                summary_sheet.write(summary_row, summary_col, bank_pay, format6)
                summary_total_bank_payment += bank_pay

                summary_col += 1
                cash_pay = round(line['cash_pay'], 2)
                summary_sheet.write(summary_row, summary_col, cash_pay, format6)
                summary_total_cash_payment += cash_pay

                #-------------------
                summary_col = 0
                summary_row = summary_row + 1

            summary_final_row = summary_row
            summary_final_col = 0
            #---------------
            summary_sheet.write(summary_final_row, summary_final_col, '', format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, 'Total', format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_emp, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_basic_salary, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_house_rent, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_medical_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_con_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_dearness_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_food_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_mobile_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_car_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_lfa_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_salbonus_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_tiffin_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_att_bonus_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_other_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_extra_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_daily_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_ota_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_bonus_alw, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_gross_salary, format7)

            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_pf, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_tds, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_advance_amount, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_loan_adj, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_loan_int_ded, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_stamp, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_abs_amt, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_join_res_ded, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_lwp_amt, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_disp_ded, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_medical_leave_ded, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_insur_ded, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_late_in_ded, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_early_out_ded, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_payable_salary, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_bank_payment, format7)
            summary_final_col += 1
            summary_sheet.write(summary_final_row, summary_final_col, summary_total_cash_payment, format7)
            #--------------

        #------------------------- Details
        for line in data['csr']:
            for line2 in line:
                sheet = workbook.add_worksheet(line[line2][0]['emp_work_location'])

                sheet.merge_range(0, 0, 0, 10, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 2, 10,
                                  "Salary Details Sheet Report (%s - %s)" % (data['start_date'], data['end_date']),
                                  format0)

                sheet.merge_range(3, 0, 3, 10, 'Work/Job Location: {0}'.format(line[line2][0]['emp_work_location']),
                                  format1)
                sheet.merge_range(4, 0, 4, 10, 'Status: {0}'.format(data['state_name']), format1)
                sheet.merge_range(5, 0, 5, 10, 'Department Name: {0}'.format(data['dept_name']), format1)


                #---------------Employee Information
                r_row_t = 6
                r_col = 0
                sheet.merge_range(r_row_t, r_col, r_row_t+1, r_col, 'Sl.', format2)
                sheet.merge_range(r_row_t, r_col+1, r_row_t, 7, 'Employee Information', format2)

                r_row = r_row_t + 1
                r_col += 1
                sheet.write(r_row, r_col, 'Employee ID', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Name', format1)
                r_col += 1
                sheet.write(r_row, r_col, 'Joining Date', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Department', format1)
                r_col += 1
                sheet.write(r_row, r_col, 'Designation', format1)
                r_col += 1
                sheet.write(r_row, r_col, 'Bank Account', format1)
                r_col += 1
                sheet.write(r_row, r_col, 'Salary Structure', format1)

                #-----------------Addition
                sheet.merge_range(r_row_t, r_col+1, r_row_t, 25, 'Addition', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Basic', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'House Rent', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Medical', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Conveyance', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Dearness', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Meal', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Mobile', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Car', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'LFA', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Salary Bonus', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Tiffin Allowances', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Att.Bonus', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Other Allowances', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Extra Allowances', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Daily Allowances', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Overtime', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Bonus', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Gross Salary', format2)

                # -----------------Deduction
                sheet.merge_range(r_row_t, r_col+1, r_row_t, 39, 'Deduction', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'PF', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'TDS', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Salary Advance', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Loan', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Loan Interest', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Stamp Fee', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Absent', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Join/Resign', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'LWP', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Disciplinary', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Medical Deduction', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Insurance', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Late IN', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Early Out', format3)

                # -----------------Attendance Information
                sheet.merge_range(r_row_t, r_col + 1, r_row_t, 53, 'Attendance Information', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Work Days', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Total Days', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Weekend', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Public Holiday', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Leave- CL', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Leave- ML', format2)
                r_col += 1
                sheet.write(r_row, r_col, 'Leave- PL', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Leave- LWP', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Present', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Absent', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Actual Late In', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Actual Early Out', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'Join/Resign', format3)
                r_col += 1
                sheet.write(r_row, r_col, 'OT Days', format3)

                #-------------------- Last part
                r_col += 1
                sheet.merge_range(r_row_t, r_col, r_row, r_col, 'Net Payable', format3)
                r_col += 1
                sheet.merge_range(r_row_t, r_col, r_row, r_col, 'Payment Type', format3)
                r_col += 1
                sheet.merge_range(r_row_t, r_col, r_row, r_col, 'Bank Payment', format3)
                r_col += 1
                sheet.merge_range(r_row_t, r_col, r_row, r_col, 'Cash Payment', format3)
                r_col += 1
                sheet.merge_range(r_row_t, r_col, r_row, r_col, 'Adjusted', format2)
                r_col += 1
                sheet.merge_range(r_row_t, r_col, r_row, r_col, 'Signature', format2)

                row = r_row+1
                col = 0

                sl_no = 1
                total_basic_salary = 0
                total_house_rent = 0
                total_medical_alw = 0
                total_con_alw = 0
                total_gross_salary = 0
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
                total_dearness_alw = 0
                total_food_alw = 0
                total_mobile_alw = 0
                total_car_alw = 0
                total_lfa_alw = 0
                total_salbonus_alw = 0
                total_tiffin_alw = 0
                total_att_bonus_alw = 0
                total_other_alw = 0
                total_extra_alw = 0
                total_daily_alw = 0
                total_ota_alw = 0
                total_bonus_alw = 0
                total_loan_int_ded = 0
                total_join_res_ded = 0
                total_disp_ded = 0
                total_insur_ded = 0
                total_late_in_ded = 0
                total_early_out_ded = 0
                total_medical_leave_ded = 0

                for line3 in line[line2]:
                    col = 0
                    sheet.write(row, col, sl_no, format5)
                    #----------- Employee Information
                    col += 1
                    sheet.write(row, col, line3['id_card_no'], format5)
                    col += 1
                    sheet.write(row, col, line3['employee_name'], format4)
                    col += 1
                    joining_date = datetime.strptime(str(line3['joining_date']), '%Y-%m-%d').strftime('%d-%b-%Y') if \
                    line3['joining_date'] else None
                    sheet.write(row, col, joining_date, format5)
                    col += 1
                    sheet.write(row, col, line3['dept_name'], format4)
                    col += 1
                    sheet.write(row, col, line3['emp_designation'], format4)
                    col += 1
                    sheet.write(row, col, line3['emp_sal_acc'], format4)
                    col += 1
                    sheet.write(row, col, line3['salary_struct'], format4)

                    # ----------- Addition
                    col += 1
                    basic_salary = round(line3['basic_salary'], 2)
                    sheet.write(row, col, basic_salary, format6)
                    total_basic_salary += basic_salary
                    grand_total_basic_salary += basic_salary

                    col += 1
                    house_rent = round(line3['house_rent'], 2)
                    sheet.write(row, col, house_rent, format6)
                    total_house_rent += house_rent
                    grand_total_house_rent += house_rent

                    col += 1
                    medical_alw = round(line3['medical_alw'], 2)
                    sheet.write(row, col, medical_alw, format6)
                    total_medical_alw += medical_alw
                    grand_total_medical_alw += medical_alw

                    col += 1
                    con_alw = round(line3['con_alw'], 2)
                    sheet.write(row, col, con_alw, format6)
                    total_con_alw += con_alw
                    grand_total_con_alw += con_alw

                    col += 1
                    dearness_alw = round(line3['dearness_alw'], 2)
                    sheet.write(row, col, dearness_alw, format6)
                    total_dearness_alw += dearness_alw
                    grand_total_dearness_alw += dearness_alw

                    col += 1
                    food_alw = round(line3['food_alw'], 2)
                    sheet.write(row, col, food_alw, format6)
                    total_food_alw += food_alw
                    grand_total_food_alw += food_alw

                    col += 1
                    mobile_alw = round(line3['mobile_alw'], 2)
                    sheet.write(row, col, mobile_alw, format6)
                    total_mobile_alw += mobile_alw
                    grand_total_mobile_alw += mobile_alw

                    col += 1
                    car_alw = round(line3['car_alw'], 2)
                    sheet.write(row, col, car_alw, format6)
                    total_car_alw += car_alw
                    grand_total_car_alw += car_alw

                    col += 1
                    lfa_alw = round(line3['lfa_alw'], 2)
                    sheet.write(row, col, lfa_alw, format6)
                    total_lfa_alw += lfa_alw
                    grand_total_lfa_alw += lfa_alw

                    col += 1
                    salbonus_alw = round(line3['salbonus_alw'], 2)
                    sheet.write(row, col, salbonus_alw, format6)
                    total_salbonus_alw += salbonus_alw
                    grand_total_salbonus_alw += salbonus_alw

                    col += 1
                    tiffin_alw = round(line3['tiffin_alw'], 2)
                    sheet.write(row, col, tiffin_alw, format6)
                    total_tiffin_alw += tiffin_alw
                    grand_total_tiffin_alw += tiffin_alw

                    col += 1
                    att_bonus_alw = round(line3['att_bonus_alw'], 2)
                    sheet.write(row, col, att_bonus_alw, format6)
                    total_att_bonus_alw += att_bonus_alw
                    grand_total_att_bonus_alw += att_bonus_alw

                    col += 1
                    other_alw = round(line3['other_alw'], 2)
                    sheet.write(row, col, other_alw, format6)
                    total_other_alw += other_alw
                    grand_total_other_alw += other_alw

                    col += 1
                    extra_alw = round(line3['extra_alw'], 2)
                    sheet.write(row, col, extra_alw, format6)
                    total_extra_alw += extra_alw
                    grand_total_extra_alw += extra_alw

                    col += 1
                    daily_alw = round(line3['daily_alw'], 2)
                    sheet.write(row, col, daily_alw, format6)
                    total_daily_alw += daily_alw
                    grand_total_daily_alw += daily_alw

                    col += 1
                    ota_alw = round(line3['ota_alw'], 2)
                    sheet.write(row, col, ota_alw, format6)
                    total_ota_alw += ota_alw
                    grand_total_ota_alw += ota_alw

                    col += 1
                    bonus_alw = round(line3['bonus_alw'], 2)
                    sheet.write(row, col, bonus_alw, format6)
                    total_bonus_alw += bonus_alw
                    grand_total_bonus_alw += bonus_alw

                    col += 1
                    gross_salary = round(line3['gross_salary'], 2)
                    sheet.write(row, col, gross_salary, format6)
                    total_gross_salary += gross_salary
                    grand_total_gross_salary += gross_salary

                    # ----------- Deduction
                    col += 1
                    pf_ded = round(line3['pf_ded'], 2)
                    sheet.write(row, col, pf_ded, format6)
                    total_pf += pf_ded
                    grand_total_pf += pf_ded

                    col += 1
                    tds_ded = round(line3['tds_ded'], 2)
                    sheet.write(row, col, tds_ded, format6)
                    total_tds += tds_ded
                    grand_total_tds += tds_ded

                    col += 1
                    adv_sal_ded = round(line3['adv_sal_ded'], 2)
                    sheet.write(row, col, adv_sal_ded, format6)
                    total_advance_amount += adv_sal_ded
                    grand_total_advance_amount += adv_sal_ded

                    col += 1
                    loan_ded = round(line3['loan_ded'], 2)
                    sheet.write(row, col, loan_ded, format6)
                    total_loan_adj += loan_ded
                    grand_total_loan_adj += loan_ded

                    col += 1
                    loan_int_ded = round(line3['loan_int_ded'], 2)
                    sheet.write(row, col, loan_int_ded, format6)
                    total_loan_int_ded += loan_int_ded
                    grand_total_loan_int_ded += loan_int_ded

                    col += 1
                    stamp_ded = round(line3['stamp_ded'], 2)
                    sheet.write(row, col, stamp_ded, format5)
                    total_stamp += stamp_ded
                    grand_total_stamp += stamp_ded

                    col += 1
                    absent_ded = round(line3['absent_ded'], 2)
                    sheet.write(row, col, absent_ded, format5)
                    total_abs_amt += absent_ded
                    grand_total_abs_amt += absent_ded

                    col += 1
                    join_res_ded = round(line3['join_res_ded'], 2)
                    sheet.write(row, col, join_res_ded, format5)
                    total_join_res_ded += join_res_ded
                    grand_total_join_res_ded += join_res_ded

                    col += 1
                    lwp_ded = round(line3['lwp_ded'], 2)
                    sheet.write(row, col, lwp_ded, format5)
                    total_lwp_amt += lwp_ded
                    grand_total_lwp_amt += lwp_ded

                    col += 1
                    disp_ded = round(line3['disp_ded'], 2)
                    sheet.write(row, col, disp_ded, format5)
                    total_disp_ded += disp_ded
                    grand_total_disp_ded += disp_ded

                    col += 1
                    medical_leave_ded = round(line3['medical_leave_ded'], 2)
                    sheet.write(row, col, medical_leave_ded, format5)
                    total_medical_leave_ded += medical_leave_ded
                    grand_total_medical_leave_ded += medical_leave_ded

                    col += 1
                    insur_ded = round(line3['insur_ded'], 2)
                    sheet.write(row, col, insur_ded, format5)
                    total_insur_ded += insur_ded
                    grand_total_insur_ded += insur_ded

                    col += 1
                    late_in_ded = round(line3['late_in_ded'], 2)
                    sheet.write(row, col, late_in_ded, format5)
                    total_late_in_ded += late_in_ded
                    grand_total_late_in_ded += late_in_ded

                    col += 1
                    early_out_ded = round(line3['early_out_ded'], 2)
                    sheet.write(row, col, early_out_ded, format5)
                    total_early_out_ded += early_out_ded
                    grand_total_early_out_ded += early_out_ded

                    # ----------- Attendance Information
                    col += 1
                    work_days = round(line3['work_days'], 0)
                    sheet.write(row, col, work_days, format6)

                    col += 1
                    total_days = round(line3['total_days'], 0)
                    sheet.write(row, col, total_days, format6)

                    col += 1
                    holy_day_wk = round(line3['holy_day_wk'], 0)
                    sheet.write(row, col, holy_day_wk, format6)

                    col += 1
                    holy_day_ph = round(line3['holy_day_ph'], 0)
                    sheet.write(row, col, holy_day_ph, format6)

                    col += 1
                    leave_cl = round(line3['leave_cl'], 0)
                    sheet.write(row, col, leave_cl, format6)

                    col += 1
                    leave_ml = round(line3['leave_ml'], 0)
                    sheet.write(row, col, leave_ml, format5)

                    col += 1
                    leave_pl = round(line3['leave_pl'], 0)
                    sheet.write(row, col, leave_pl, format5)

                    col += 1
                    leave_lwp = round(line3['leave_lwp'], 0)
                    sheet.write(row, col, leave_lwp, format5)

                    col += 1
                    no_presence = round(line3['no_presence'], 0)
                    sheet.write(row, col, no_presence, format5)

                    col += 1
                    no_absence = round(line3['no_absence'], 0)
                    sheet.write(row, col, no_absence, format5)

                    col += 1
                    actual_late = round(line3['actual_late'], 0)
                    sheet.write(row, col, actual_late, format5)

                    col += 1
                    actual_early_out = round(line3['actual_early_out'], 0)
                    sheet.write(row, col, actual_early_out, format5)

                    col += 1
                    no_join_resign = round(line3['no_join_resign'], 0)
                    sheet.write(row, col, no_join_resign, format5)

                    col += 1
                    no_overtime = round(line3['no_overtime'], 0)
                    sheet.write(row, col, no_overtime, format5)
                    #-------------------
                    col += 1
                    total_net_sal = round(line3['total_net_sal'], 2)
                    sheet.write(row, col, total_net_sal, format5)
                    total_payable_salary += total_net_sal
                    grand_total_payable_salary += total_net_sal

                    col += 1
                    sheet.write(row, col, line3['payment_type'], format5)

                    col += 1
                    bank_pay = round(line3['bank_pay'], 2)
                    sheet.write(row, col, bank_pay, format6)
                    total_bank_payment += bank_pay
                    grand_total_bank_payment += bank_pay

                    col += 1
                    cash_pay = round(line3['cash_pay'], 2)
                    sheet.write(row, col, cash_pay, format6)
                    total_cash_payment += cash_pay
                    grand_total_cash_payment += cash_pay

                    col += 1
                    sheet.write(row, col, None, format5)
                    col += 1
                    sheet.write(row, col, None, format5)

                    row = row + 1
                    sl_no = sl_no + 1
                    grand_total_emp += 1

                final_row = row
                final_col = 0

                sheet.merge_range(final_row, final_col, final_row, final_col + 7, 'TOTAL', format7)
                final_col += 8
                sheet.write(final_row, final_col, total_basic_salary, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_house_rent, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_medical_alw, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_con_alw, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_dearness_alw, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_food_alw, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_mobile_alw, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_car_alw, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_lfa_alw, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_salbonus_alw, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_tiffin_alw, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_att_bonus_alw, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_other_alw, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_extra_alw, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_daily_alw, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_ota_alw, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_bonus_alw, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_gross_salary, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_pf, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_tds, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_advance_amount, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_loan_adj, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_loan_int_ded, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_stamp, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_abs_amt, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_join_res_ded, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_lwp_amt, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_disp_ded, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_medical_leave_ded, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_insur_ded, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_late_in_ded, format9)
                final_col += 1
                sheet.write(final_row, final_col, total_early_out_ded, format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, total_payable_salary, format9)
                final_col += 1
                sheet.write(final_row, final_col, '', format9)
                final_col += 1
                sheet.write(final_row, final_col, total_bank_payment, format7)
                final_col += 1
                sheet.write(final_row, final_col, total_cash_payment, format7)

                final_col += 1
                sheet.merge_range(final_row, final_col, final_row, final_col + 1, None, format7)

        sheet = workbook.add_worksheet('Grand Total')

        sheet.merge_range(0, 0, 1, 10, 'GRAND TOTAL', format9)
        sheet.merge_range(2, 0, 2, 10, 'Branch/Work/Job Location: {0}'.format(data['work_loc_name']), format1)
        sheet.merge_range(3, 0, 3, 10, 'Status: {0}'.format(data['state_name']), format1)
        sheet.merge_range(4, 0, 4, 10, 'Department Name: {0}'.format(data['dept_name']), format1)

        r_row = 5
        r_col = 0
        sheet.write(r_row, r_col, 'Total Employee', format7)
        r_col += 1
        sheet.write(r_row, r_col, 'Basic', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'House Rent', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Medical', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Conveyance', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Dearness', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Meal', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Mobile', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Car', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'LFA', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Salary Bonus', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Tiffin Allowances', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Att.Bonus', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Other Allowances', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Extra Allowances', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Daily Allowances', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Overtime', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Bonus', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Gross Salary', format2)

        # -----------------Deduction
        r_col += 1
        sheet.write(r_row, r_col, 'PF', format2)
        r_col += 1
        sheet.write(r_row, r_col, 'TDS', format2)
        r_col += 1
        sheet.write(r_row, r_col, 'Salary Advance', format2)
        r_col += 1
        sheet.write(r_row, r_col, 'Loan', format2)
        r_col += 1
        sheet.write(r_row, r_col, 'Loan Interest', format2)
        r_col += 1
        sheet.write(r_row, r_col, 'Stamp Fee', format2)
        r_col += 1
        sheet.write(r_row, r_col, 'Absent', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Join/Resign', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'LWP', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Disciplinary', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Medical Deduction', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Insurance', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Late IN', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Early Out', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Net Payable', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Bank Payment', format3)
        r_col += 1
        sheet.write(r_row, r_col, 'Cash Payment', format3)

        r_row += 1
        r_col = 0
        sheet.write(r_row, r_col, grand_total_emp, format9)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_basic_salary, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_house_rent, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_medical_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_con_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_dearness_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_food_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_mobile_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_car_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_lfa_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_salbonus_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_tiffin_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_att_bonus_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_other_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_extra_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_daily_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_ota_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_bonus_alw, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_gross_salary, format7)

        r_col += 1
        sheet.write(r_row, r_col, grand_total_pf, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_tds, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_advance_amount, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_loan_adj, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_loan_int_ded, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_stamp, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_abs_amt, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_join_res_ded, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_lwp_amt, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_disp_ded, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_medical_leave_ded, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_insur_ded, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_late_in_ded, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_early_out_ded, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_payable_salary, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_bank_payment, format7)
        r_col += 1
        sheet.write(r_row, r_col, grand_total_cash_payment, format7)


        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Detail Salary Sheet Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=salary.details.sheet.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def salary_details_sheet_report_sql(self, month, year, department_id, state, user_work_location_id, include_zero_less_payable, report_type, employee_id):
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
                    """.format(start_date, end_date, state_filter, dept_filter2, work_loc_filter, include_non_zero_payable_filter, report_type_filter, emp_filter)
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
                            """.format(start_date, end_date, state_filter, dept_filter2, work_loc_filter, include_non_zero_payable_filter, report_type_filter, emp_filter)
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
        }
        return data
