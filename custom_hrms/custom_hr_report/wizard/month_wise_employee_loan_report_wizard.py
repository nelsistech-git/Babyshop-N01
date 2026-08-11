from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import datetime
from datetime import datetime
import copy
from itertools import groupby
import xlsxwriter

import base64
from io import BytesIO
import pandas as pd

class MonthWiseEmployeeLoanReportWizard(models.TransientModel):
    _name = "month.wise.employee.loan.report.wizard"
    _description = "Month Wise Employee Loan Report Wizard"

    file_data = fields.Binary('Month Wise Employee Loan Report Wizard')

    fiscalyear_id = fields.Many2one('account.fiscal.year', required=True, string='Fiscal Year')
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)
    month_count = fields.Integer(string="Number of Months", default=0)
    loan_type_id = fields.Many2one('employee.loan.type', string='Loan Type')

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', default=lambda self: self._get_work_loc(), domain=lambda self: self._set_domain_work_loc())
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')

    @api.onchange('fiscalyear_id')
    def onchange_fiscalyear(self):
        if self.fiscalyear_id:
            self.date_from = self.fiscalyear_id.date_from
            self.date_to = self.fiscalyear_id.date_to
        else:
            self.date_from = None
            self.date_to = None

    @api.onchange('date_from', 'date_to')
    def onchange_date_from_to(self):
        if self.date_from and self.date_to:
            month_list = pd.period_range(start=self.date_from, end=self.date_to, freq='M')
            month_list = [month.strftime("%Y-%m") for month in month_list]
            self.month_count = len(month_list)
        else:
            self.month_count = 0

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

    @api.onchange('user_user_work_location_id', 'department_id')
    def _onchange_employees(self):
        domain = []

        if self.user_work_location_id:
            domain += [('user_work_location_id', '=', self.user_work_location_id.id)]

        if self.department_id:
            domain += [('department_id', '=', self.department_id.id)]

        return {'domain': {
            'employee_id': domain,
        }}


    def month_wise_loan_report_excel(self):
        year = self.fiscalyear_id.name or None
        date_from = self.date_from
        date_to = self.date_to
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id
        loan_type_id = self.loan_type_id
        month_count = self.month_count
        if month_count !=12:
            raise UserError(_('Required 12 months of this search period'))

        # get data from sql
        data = self.employee_loan_report_sql(date_from, date_to, user_work_location_id, department_id, employee_id, loan_type_id)


        file_name = "Month Wise Employee Loan Report - %s.xlsx" % year
        file_pointer = BytesIO()

        workbook = xlsxwriter.Workbook(file_pointer)

        # main header formatting
        format0 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
        format0.set_align('left')
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

        sheet = workbook.add_worksheet('Month wise Employee Loan Report-%s' % year)

        head_row = 5
        head_col = 0
        m_row = 4
        #----------Employee Information
        sheet.merge_range(m_row, 0, m_row, 7, 'Employee Information', format2)
        sheet.write(head_row, head_col, 'Emp ID', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Name of Employee', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Work Location', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Department', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Designation', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'E-TIN', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Date of Joining', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Date of Membership', format1)

        #-------------------- loan information
        sheet.merge_range(m_row, 8, m_row, 19, 'Loan Information', format2)
        head_col += 1
        sheet.write(head_row, head_col, 'Loan Type', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Loan Ref.', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Start Date', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Loan Amount', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Process fee', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Number of Installment', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Installment Amount', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Paid Installment', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Paid Amount', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Remaining Installment', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Remaining Amount', format1)
        head_col += 1
        sheet.write(head_row, head_col, 'Status', format1)

        #-------------------
        month_list = data['month_view']

        m_col1=20
        m_col2=22
        sheet.merge_range(m_row, m_col1, m_row, m_col2, 'Opening', format2)
        head_col += 1
        sheet.write(head_row, head_col, 'Opening (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, 'Opening (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, 'Opening (Total)', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[0], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[0]+' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[0] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[0] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[1], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[1] + ' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[1] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[1] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[2], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[2] + ' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[2] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[2] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[3], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[3] + ' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[3] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[3] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[4], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[4] + ' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[4] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[4] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[5], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[5] + ' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[5] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[5] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[6], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[6] + ' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[6] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[6] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[7], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[7] + ' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[7] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[7] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[8], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[8] + ' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[8] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[8] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[9], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[9] + ' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[9] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[9] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[10], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[10] + ' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[10] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[10] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, month_list[11], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[11] + ' (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[11] + ' (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[11] + ' Total', format3)

        m_col1 += 3
        m_col2 += 3
        sheet.merge_range(m_row, m_col1, m_row, m_col2, 'Closing', format2)
        head_col += 1
        sheet.write(head_row, head_col, 'Closing (Amount)', format3)
        head_col += 1
        sheet.write(head_row, head_col, 'Closing (Interest)', format3)
        head_col += 1
        sheet.write(head_row, head_col, 'Closing Total', format3)

        sheet.merge_range(0, 0, 0, head_col, "Month Wise Employee Loan Report - {0}".format(year), format0)
        sheet.merge_range(1, 0, 1, head_col, "Work Location: {0}".format(data['work_location_name']), format1)
        sheet.merge_range(2, 0, 2, head_col, "Department: {0}".format(data['dept_name']), format1)
        sheet.merge_range(3, 0, 3, head_col, "Loan Type: {0}".format(data['loan_type']), format1)

        #-------------grand total
        op_amt_net=0
        m1_amt_net=0
        m2_amt_net=0
        m3_amt_net=0
        m4_amt_net=0
        m5_amt_net=0
        m6_amt_net=0
        m7_amt_net=0
        m8_amt_net=0
        m9_amt_net=0
        m10_amt_net=0
        m11_amt_net=0
        m12_amt_net=0

        op_interest_net = 0
        m1_interest_net=0
        m2_interest_net=0
        m3_interest_net=0
        m4_interest_net=0
        m5_interest_net=0
        m6_interest_net=0
        m7_interest_net=0
        m8_interest_net=0
        m9_interest_net=0
        m10_interest_net=0
        m11_interest_net=0
        m12_interest_net=0

        cl_amt_net = 0
        cl_interest_net = 0
        #--------------
        row = 6
        col = 0
        for rec in data['csr']:
            #---------- employee information
            sheet.write(row, col, rec['emp_card'], format4)
            col += 1
            sheet.write(row, col, rec['emp_name'], format4)
            col += 1
            sheet.write(row, col, rec['wloc_name'], format4)
            col += 1
            sheet.write(row, col, rec['dept_name'], format4)
            col += 1
            sheet.write(row, col, rec['desig_name'], format4)
            col += 1
            etin = str(rec['etin']) if rec['etin'] else ''
            sheet.write(row, col, etin, format4)
            col += 1
            join_date = str(rec['join_date']) if rec['join_date'] else ''
            sheet.write(row, col, join_date, format4)
            col += 1
            pf_start_date=str(rec['pf_start_date']) if rec['pf_start_date'] else ''
            sheet.write(row, col,pf_start_date , format4)

            #---------- loan information
            col += 1
            sheet.write(row, col, rec['type_name'], format4)
            col += 1
            sheet.write(row, col, rec['loan_ref'], format4)
            col += 1
            sheet.write(row, col, str(rec['start_date']) if rec['start_date'] else '', format4)
            col += 1
            sheet.write(row, col, rec['loan_amount'], format6)
            col += 1
            sheet.write(row, col, 0, format6)
            col += 1
            sheet.write(row, col, rec['inst_count'], format6)
            col += 1
            sheet.write(row, col, round(rec['installment_amount'], 2), format6)
            col += 1
            sheet.write(row, col, rec['paid_count'], format6)
            col += 1
            sheet.write(row, col, rec['paid_amount'], format6)
            col += 1
            sheet.write(row, col, rec['inst_count'] - rec['paid_count'], format6)
            col += 1
            sheet.write(row, col, rec['remaining_amount'], format6)
            col += 1
            state_val = ''
            if rec['state'] =='close':
                state_val = 'Closed'
            elif rec['state'] =='done':
                state_val = 'Running'
            sheet.write(row, col,state_val, format1)

            # ---------- details information
            op_amt = round(rec['op_amt'], 2)
            op_interest = round(rec['op_interest'], 2)
            op_total = op_amt + op_interest
            op_amt_net += op_amt
            op_interest_net += op_interest
            col += 1
            sheet.write(row, col, op_amt, format6)
            col += 1
            sheet.write(row, col, op_interest, format6)
            col += 1
            sheet.write(row, col, op_total, format7)

            m1_amt = round(rec['m1_amt'], 2)
            m1_interest = round(rec['m1_interest'], 2)
            m1_total = m1_amt + m1_interest
            m1_amt_net += m1_amt
            m1_interest_net += m1_interest
            col += 1
            sheet.write(row, col, m1_amt, format6)
            col += 1
            sheet.write(row, col, m1_interest, format6)
            col += 1
            sheet.write(row, col, m1_total, format7)

            m2_amt = round(rec['m2_amt'], 2)
            m2_interest = round(rec['m2_interest'], 2)
            m2_total = m2_amt + m2_interest
            m2_amt_net += m2_amt
            m2_interest_net += m2_interest
            col += 1
            sheet.write(row, col, m2_amt, format6)
            col += 1
            sheet.write(row, col, m2_interest, format6)
            col += 1
            sheet.write(row, col, m2_total, format7)

            m3_amt = round(rec['m3_amt'], 2)
            m3_interest = round(rec['m3_interest'], 2)
            m3_total = m3_amt + m3_interest
            m3_amt_net += m3_amt
            m3_interest_net += m3_interest
            col += 1
            sheet.write(row, col, m3_amt, format6)
            col += 1
            sheet.write(row, col, m3_interest, format6)
            col += 1
            sheet.write(row, col, m3_total, format7)

            m4_amt = round(rec['m4_amt'], 2)
            m4_interest = round(rec['m4_interest'], 2)
            m4_total = m4_amt + m4_interest
            m4_amt_net += m4_amt
            m4_interest_net += m4_interest
            col += 1
            sheet.write(row, col, m4_amt, format6)
            col += 1
            sheet.write(row, col, m4_interest, format6)
            col += 1
            sheet.write(row, col, m4_total, format7)

            m5_amt = round(rec['m5_amt'], 2)
            m5_interest = round(rec['m5_interest'], 2)
            m5_total = m5_amt + m5_interest
            m5_amt_net += m5_amt
            m5_interest_net += m5_interest
            col += 1
            sheet.write(row, col, m5_amt, format6)
            col += 1
            sheet.write(row, col, m5_interest, format6)
            col += 1
            sheet.write(row, col, m5_total, format7)

            m6_amt = round(rec['m6_amt'], 2)
            m6_interest = round(rec['m6_interest'], 2)
            m6_total = m6_amt + m6_interest
            m6_amt_net += m6_amt
            m6_interest_net += m6_interest
            col += 1
            sheet.write(row, col, m6_amt, format6)
            col += 1
            sheet.write(row, col, m6_interest, format6)
            col += 1
            sheet.write(row, col, m6_total, format7)

            m7_amt = round(rec['m7_amt'], 2)
            m7_interest = round(rec['m7_interest'], 2)
            m7_total = m7_amt + m7_interest
            m7_amt_net += m7_amt
            m7_interest_net += m7_interest
            col += 1
            sheet.write(row, col, m7_amt, format6)
            col += 1
            sheet.write(row, col, m7_interest, format6)
            col += 1
            sheet.write(row, col, m7_total, format7)

            m8_amt = round(rec['m8_amt'], 2)
            m8_interest = round(rec['m8_interest'], 2)
            m8_total = m8_amt + m8_interest
            m8_amt_net += m8_amt
            m8_interest_net += m8_interest
            col += 1
            sheet.write(row, col, m8_amt, format6)
            col += 1
            sheet.write(row, col, m8_interest, format6)
            col += 1
            sheet.write(row, col, m8_total, format7)

            m9_amt = round(rec['m9_amt'], 2)
            m9_interest = round(rec['m9_interest'], 2)
            m9_total = m9_amt + m9_interest
            m9_amt_net += m9_amt
            m9_interest_net += m9_interest
            col += 1
            sheet.write(row, col, m9_amt, format6)
            col += 1
            sheet.write(row, col, m9_interest, format6)
            col += 1
            sheet.write(row, col, m9_total, format7)

            m10_amt = round(rec['m10_amt'], 2)
            m10_interest = round(rec['m10_interest'], 2)
            m10_total = m10_amt + m10_interest
            m10_amt_net += m10_amt
            m10_interest_net += m10_interest
            col += 1
            sheet.write(row, col, m10_amt, format6)
            col += 1
            sheet.write(row, col, m10_interest, format6)
            col += 1
            sheet.write(row, col, m10_total, format7)

            m11_amt = round(rec['m11_amt'], 2)
            m11_interest = round(rec['m11_interest'], 2)
            m11_total = m11_amt + m11_interest
            m11_amt_net += m11_amt
            m11_interest_net += m11_interest
            col += 1
            sheet.write(row, col, m11_amt, format6)
            col += 1
            sheet.write(row, col, m11_interest, format6)
            col += 1
            sheet.write(row, col, m11_total, format7)

            m12_amt = round(rec['m12_amt'], 2)
            m12_interest = round(rec['m12_interest'], 2)
            m12_total = m12_amt + m12_interest
            m12_amt_net += m12_amt
            m12_interest_net += m12_interest
            col += 1
            sheet.write(row, col, m12_amt, format6)
            col += 1
            sheet.write(row, col, m12_interest, format6)
            col += 1
            sheet.write(row, col, m12_total, format7)

            cl_amt = op_amt + m1_amt + m2_amt + m3_amt + m4_amt + m5_amt + m6_amt + m7_amt + m8_amt + m9_amt + m10_amt + m11_amt + m12_amt
            cl_interest = op_interest + m1_interest + m2_interest + m3_interest + m4_interest + m5_interest + m6_interest + m7_interest + m8_interest + m9_interest + m10_interest + m11_interest + m12_interest
            cl_total = cl_amt + cl_interest

            cl_amt_net += cl_amt
            cl_interest_net += cl_interest

            col += 1
            sheet.write(row, col, cl_amt, format6)
            col += 1
            sheet.write(row, col, cl_interest, format6)
            col += 1
            sheet.write(row, col, cl_total, format7)

            row = row + 1
            col = 0

        #------------------- Grand Total
        final_row = row
        final_col = 0
        sheet.merge_range(final_row, final_col, final_row, final_col + 19, 'TOTAL', format7)
        final_col += 20
        sheet.write(final_row, final_col, op_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, op_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, op_amt_net + op_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m1_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m1_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m1_amt_net + m1_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m2_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m2_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m2_amt_net + m2_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m3_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m3_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m3_amt_net + m3_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m4_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m4_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m4_amt_net + m4_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m5_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m5_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m5_amt_net + m5_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m6_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m6_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m6_amt_net + m6_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m7_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m7_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m7_amt_net + m7_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m8_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m8_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m8_amt_net + m8_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m9_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m9_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m9_amt_net + m9_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m10_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m10_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m10_amt_net + m10_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m11_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m11_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m11_amt_net + m11_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m12_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m12_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m12_amt_net + m12_interest_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, cl_amt_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, cl_interest_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, cl_amt_net + cl_interest_net, format7)


        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Month Wise Employee Loan Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=month.wise.employee.loan.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_loan_report_sql(self, date_from, date_to, user_work_location_id, department_id, employee_id, loan_type_id):
        year = self.fiscalyear_id.name
        work_location_name = "All"
        dept_name = "All"
        loan_type = "All"
        filter = ""

        filter = "WHERE loanh.state in ('done','close')"
        filter += " AND loanl.is_paid = True"

        if loan_type_id:
            filter = " AND loanh.loan_type_id = %s" % loan_type_id.id
            loan_type = loan_type_id.name

        if user_work_location_id:
            filter += " AND emp.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if department_id:
            filter += " AND emp.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if employee_id:
            filter += " AND loanh.employee_id = %s" % employee_id.id

        month_list1 = pd.period_range(start=date_from, end=date_to, freq='M')
        month_list = []
        month_view = []
        for month in month_list1:
            month_list.append(month.strftime("%Y-%m"))
            month_view.append(month.strftime("%b'%y"))

        data_sql = """
                SELECT loanh.id,loanh.name as loan_ref,loant.name as type_name,loanh.start_date as start_date,loanh.loan_amount,loanh.term as inst_count,loanh.installment_amount,loanh.paid_count,loanh.paid_amount,loanh.remaing_amount as remaining_amount,loanh.state,loanh.employee_id,emp.id_card_no as emp_card,emp.name as emp_name,dept.name->>'en_US' as dept_name,desig.name->>'en_US' as desig_name,wloc.name as wloc_name,
                emp.initial_employment_date as join_date,emp.tax_id as etin,emp.pf_start_date as pf_start_date,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') < '{0}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS op_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') < '{0}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS op_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{0}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m1_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{0}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m1_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{1}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m2_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{1}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m2_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{2}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m3_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{2}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m3_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{3}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m4_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{3}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m4_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{4}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m5_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{4}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m5_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{5}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m6_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{5}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m6_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{6}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m7_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{6}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m7_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{7}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m8_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{7}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m8_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{8}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m9_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{8}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m9_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{9}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m10_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{9}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m10_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{10}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m11_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{10}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m11_interest,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{11}' THEN COALESCE(installment_amt, 0) ELSE 0 END) AS m12_amt,
                SUM(CASE WHEN TO_CHAR(paid_date, 'YYYY-MM') = '{11}' THEN COALESCE(ins_interest, 0) ELSE 0 END) AS m12_interest
                from employee_loan loanh
                LEFT JOIN installment_line loanl ON loanh.id = loanl.loan_id
                LEFT JOIN employee_loan_type loant ON loanh.loan_type_id = loant.id
                LEFT JOIN hr_employee emp ON loanh.employee_id = emp.id
                LEFT JOIN hr_department dept ON emp.department_id = dept.id
                LEFT JOIN hr_job desig ON emp.job_id = desig.id
                LEFT JOIN stock_location wloc ON emp.user_work_location_id = wloc.id
                {12}
                GROUP BY loanh.id,loanh.name,loant.name,loanh.start_date,loanh.loan_amount,loanh.term,loanh.installment_amount,loanh.paid_count,loanh.paid_amount,loanh.remaing_amount,loanh.state,loanh.employee_id,emp.id_card_no, emp.name,dept.name,desig.name,wloc.name,emp.initial_employment_date,emp.tax_id,emp.pf_start_date
                ORDER BY emp.id_card_no, loanh.start_date;
                """.format(month_list[0], month_list[1], month_list[2], month_list[3], month_list[4],
                           month_list[5], month_list[6], month_list[7], month_list[8], month_list[9],
                           month_list[10], month_list[11],filter)
        self.env.cr.execute(data_sql)
        data_list = self.env.cr.dictfetchall()
        data = {
            'model': 'month.wise.employee.loan.report.wizard',
            'form': self.read()[0],
            'csr': data_list,
            'month_list': month_list,
            'month_view': month_view,
            'work_location_name': work_location_name,
            'dept_name': dept_name,
            'year': year,
            'loan_type': loan_type
        }

        return data
