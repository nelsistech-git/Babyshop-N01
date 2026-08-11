from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import datetime
from datetime import datetime
import copy
from itertools import groupby
import xlsxwriter
import math

import base64
from io import BytesIO
import pandas as pd

class MonthWiseEmployeePFReportWizard(models.TransientModel):
    _name = "month.wise.employee.pf.report.wizard"
    _description = "Month Wise Employee PF Report Wizard"

    file_data = fields.Binary('Month Wise Employee PF Report Wizard')

    fiscalyear_id = fields.Many2one('account.fiscal.year', required=True, string='Fiscal Year')
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)
    month_count = fields.Integer(string="Number of Months", default=0)
    contribution_type = fields.Selection([('all', 'ALL'), ('salary', 'Salary'), ('profit', 'Profit')],
                                         string='Contribution Type', default='all', required=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', default=lambda self: self._get_work_loc(), domain=lambda self: self._set_domain_work_loc())
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')

    category_ids = fields.Many2many('hr.employee.category', 'month_wise_employee_pf_employee_category_rel', 
                'selected_id', 'category_id', string='Tags')

    sbu_unit_id = fields.Many2one('hr.sbu.unit', string='Office/Business Unit')

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


    def month_wise_pf_report_excel(self):
        year = self.fiscalyear_id.name or None
        date_from = self.date_from
        date_to = self.date_to
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id
        contribution_type = self.contribution_type
        month_count = self.month_count
        if month_count !=12:
            raise UserError(_('Required 12 months of this search period'))

        # get data from sql
        data = self.employee_pf_report_sql(date_from, date_to, user_work_location_id, department_id, employee_id, contribution_type)


        file_name = "Month Wise Employee PF Report - %s.xlsx" % year
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

        sheet = workbook.add_worksheet('Month wise Employee PF Report-%s' % year)

        head_row = 5
        head_col = 0

        sheet.merge_range(4, 0, 4, 7, 'Employee Information', format2)
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

        #-------------------
        month_list = data['month_view']

        sheet.merge_range(4, 8, 4, 10, 'Opening', format2)
        head_col += 1
        sheet.write(head_row, head_col, 'Opening (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, 'Opening (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, 'Opening (Total)', format3)

        sheet.merge_range(4, 11, 4, 13, month_list[0], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[0]+' (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[0] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[0] + ' Total', format3)

        sheet.merge_range(4, 14, 4, 16, month_list[1], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[1] + ' (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[1] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[1] + ' Total', format3)

        sheet.merge_range(4, 17, 4, 19, month_list[2], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[2] + ' PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[2] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[2] + ' Total', format3)

        sheet.merge_range(4, 20, 4, 22, month_list[3], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[3] + ' (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[3] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[3] + ' Total', format3)

        sheet.merge_range(4, 23, 4, 25, month_list[4], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[4] + ' (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[4] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[4] + ' Total', format3)

        sheet.merge_range(4, 26, 4, 28, month_list[5], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[5] + ' (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[5] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[5] + ' Total', format3)

        sheet.merge_range(4, 29, 4, 31, month_list[6], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[6] + ' (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[6] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[6] + ' Total', format3)

        sheet.merge_range(4, 32, 4, 34, month_list[7], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[7] + ' (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[7] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[7] + ' Total', format3)

        sheet.merge_range(4, 35, 4, 37, month_list[8], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[8] + ' (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[8] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[8] + ' Total', format3)

        sheet.merge_range(4, 38, 4, 40, month_list[9], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[9] + ' (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[9] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[9] + ' Total', format3)

        sheet.merge_range(4, 41, 4, 43, month_list[10], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[10] + ' (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[10] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[10] + ' Total', format3)

        sheet.merge_range(4, 44, 4, 46, month_list[11], format2)
        head_col += 1
        sheet.write(head_row, head_col, month_list[11] + ' (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[11] + ' (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, month_list[11] + ' Total', format3)

        sheet.merge_range(4, 47, 4, 49, 'Closing', format2)
        head_col += 1
        sheet.write(head_row, head_col, 'Closing (PF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, 'Closing (CPF)', format3)
        head_col += 1
        sheet.write(head_row, head_col, 'Closing Total', format3)

        sheet.merge_range(0, 0, 0, head_col, "Month Wise Employee PF Report - {0}".format(year), format0)

        sheet.merge_range(1, 0, 1, math.floor(head_col/2), "Work Location: {0}".format(data['work_location_name']), format1)
        sheet.merge_range(2, 0, 2, math.floor(head_col/2), "Department: {0}".format(data['dept_name']), format1)
        sheet.merge_range(3, 0, 3, math.floor(head_col/2), "Contribution Type: {0}".format(data['contribution_type']), format1)

        sheet.merge_range(1, math.floor(head_col/2) + 1, 1, head_col, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
        sheet.merge_range(2, math.floor(head_col/2) + 1, 2, head_col, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)
        sheet.merge_range(3, math.floor(head_col/2) + 1, 3, head_col, None, format1)


        #-------------grand total
        op_pf_net=0
        m1_pf_net=0
        m2_pf_net=0
        m3_pf_net=0
        m4_pf_net=0
        m5_pf_net=0
        m6_pf_net=0
        m7_pf_net=0
        m8_pf_net=0
        m9_pf_net=0
        m10_pf_net=0
        m11_pf_net=0
        m12_pf_net=0

        op_cpf_net = 0
        m1_cpf_net=0
        m2_cpf_net=0
        m3_cpf_net=0
        m4_cpf_net=0
        m5_cpf_net=0
        m6_cpf_net=0
        m7_cpf_net=0
        m8_cpf_net=0
        m9_cpf_net=0
        m10_cpf_net=0
        m11_cpf_net=0
        m12_cpf_net=0

        cl_pf_net = 0
        cl_cpf_net = 0
        #--------------
        row = 6
        col = 0
        for rec in data['csr']:
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
            #----------
            op_pf = rec['op_pf']
            op_cpf = rec['op_cpf']
            op_total = op_pf + op_cpf
            op_pf_net += op_pf
            op_cpf_net += op_cpf
            col += 1
            sheet.write(row, col, op_pf, format6)
            col += 1
            sheet.write(row, col, op_cpf, format6)
            col += 1
            sheet.write(row, col, op_total, format7)



            m1_pf = rec['m1_pf']
            m1_cpf = rec['m1_cpf']
            m1_total = m1_pf + m1_cpf
            m1_pf_net += m1_pf
            m1_cpf_net += m1_cpf
            col += 1
            sheet.write(row, col, m1_pf, format6)
            col += 1
            sheet.write(row, col, m1_cpf, format6)
            col += 1
            sheet.write(row, col, m1_total, format7)

            m2_pf = rec['m2_pf']
            m2_cpf = rec['m2_cpf']
            m2_total = m2_pf + m2_cpf
            m2_pf_net += m2_pf
            m2_cpf_net += m2_cpf
            col += 1
            sheet.write(row, col, m2_pf, format6)
            col += 1
            sheet.write(row, col, m2_cpf, format6)
            col += 1
            sheet.write(row, col, m2_total, format7)

            m3_pf = rec['m3_pf']
            m3_cpf = rec['m3_cpf']
            m3_total = m3_pf + m3_cpf
            m3_pf_net += m3_pf
            m3_cpf_net += m3_cpf
            col += 1
            sheet.write(row, col, m3_pf, format6)
            col += 1
            sheet.write(row, col, m3_cpf, format6)
            col += 1
            sheet.write(row, col, m3_total, format7)

            m4_pf = rec['m4_pf']
            m4_cpf = rec['m4_cpf']
            m4_total = m4_pf + m4_cpf
            m4_pf_net += m4_pf
            m4_cpf_net += m4_cpf
            col += 1
            sheet.write(row, col, m4_pf, format6)
            col += 1
            sheet.write(row, col, m4_cpf, format6)
            col += 1
            sheet.write(row, col, m4_total, format7)

            m5_pf = rec['m5_pf']
            m5_cpf = rec['m5_cpf']
            m5_total = m5_pf + m5_cpf
            m5_pf_net += m5_pf
            m5_cpf_net += m5_cpf
            col += 1
            sheet.write(row, col, m5_pf, format6)
            col += 1
            sheet.write(row, col, m5_cpf, format6)
            col += 1
            sheet.write(row, col, m5_total, format7)

            m6_pf = rec['m6_pf']
            m6_cpf = rec['m6_cpf']
            m6_total = m6_pf + m6_cpf
            m6_pf_net += m6_pf
            m6_cpf_net += m6_cpf
            col += 1
            sheet.write(row, col, m6_pf, format6)
            col += 1
            sheet.write(row, col, m6_cpf, format6)
            col += 1
            sheet.write(row, col, m6_total, format7)

            m7_pf = rec['m7_pf']
            m7_cpf = rec['m7_cpf']
            m7_total = m7_pf + m7_cpf
            m7_pf_net += m7_pf
            m7_cpf_net += m7_cpf
            col += 1
            sheet.write(row, col, m7_pf, format6)
            col += 1
            sheet.write(row, col, m7_cpf, format6)
            col += 1
            sheet.write(row, col, m7_total, format7)

            m8_pf = rec['m8_pf']
            m8_cpf = rec['m8_cpf']
            m8_total = m8_pf + m8_cpf
            m8_pf_net += m8_pf
            m8_cpf_net += m8_cpf
            col += 1
            sheet.write(row, col, m8_pf, format6)
            col += 1
            sheet.write(row, col, m8_cpf, format6)
            col += 1
            sheet.write(row, col, m8_total, format7)

            m9_pf = rec['m9_pf']
            m9_cpf = rec['m9_cpf']
            m9_total = m9_pf + m9_cpf
            m9_pf_net += m9_pf
            m9_cpf_net += m9_cpf
            col += 1
            sheet.write(row, col, m9_pf, format6)
            col += 1
            sheet.write(row, col, m9_cpf, format6)
            col += 1
            sheet.write(row, col, m9_total, format7)

            m10_pf = rec['m10_pf']
            m10_cpf = rec['m10_cpf']
            m10_total = m10_pf + m10_cpf
            m10_pf_net += m10_pf
            m10_cpf_net += m10_cpf
            col += 1
            sheet.write(row, col, m10_pf, format6)
            col += 1
            sheet.write(row, col, m10_cpf, format6)
            col += 1
            sheet.write(row, col, m10_total, format7)

            m11_pf = rec['m11_pf']
            m11_cpf = rec['m11_cpf']
            m11_total = m11_pf + m11_cpf
            m11_pf_net += m11_pf
            m11_cpf_net += m11_cpf
            col += 1
            sheet.write(row, col, m11_pf, format6)
            col += 1
            sheet.write(row, col, m11_cpf, format6)
            col += 1
            sheet.write(row, col, m11_total, format7)

            m12_pf = rec['m12_pf']
            m12_cpf = rec['m12_cpf']
            m12_total = m12_pf + m12_cpf
            m12_pf_net += m12_pf
            m12_cpf_net += m12_cpf
            col += 1
            sheet.write(row, col, m12_pf, format6)
            col += 1
            sheet.write(row, col, m12_cpf, format6)
            col += 1
            sheet.write(row, col, m12_total, format7)

            cl_pf = op_pf + m1_pf + m2_pf + m3_pf + m4_pf + m5_pf + m6_pf + m7_pf + m8_pf + m9_pf + m10_pf + m11_pf + m12_pf
            cl_cpf = op_cpf + m1_cpf + m2_cpf + m3_cpf + m4_cpf + m5_cpf + m6_cpf + m7_cpf + m8_cpf + m9_cpf + m10_cpf + m11_cpf + m12_cpf
            cl_total = cl_pf + cl_cpf

            cl_pf_net += cl_pf
            cl_cpf_net += cl_cpf

            col += 1
            sheet.write(row, col, cl_pf, format6)
            col += 1
            sheet.write(row, col, cl_cpf, format6)
            col += 1
            sheet.write(row, col, cl_total, format7)

            row = row + 1
            col = 0

        #------------------- Grand Total
        final_row = row
        final_col = 0
        sheet.merge_range(final_row, final_col, final_row, final_col + 7, 'TOTAL', format7)
        final_col += 8
        sheet.write(final_row, final_col, op_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, op_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, op_pf_net + op_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m1_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m1_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m1_pf_net + m1_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m2_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m2_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m2_pf_net + m2_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m3_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m3_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m3_pf_net + m3_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m4_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m4_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m4_pf_net + m4_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m5_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m5_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m5_pf_net + m5_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m6_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m6_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m6_pf_net + m6_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m7_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m7_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m7_pf_net + m7_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m8_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m8_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m8_pf_net + m8_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m9_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m9_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m9_pf_net + m9_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m10_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m10_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m10_pf_net + m10_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m11_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m11_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m11_pf_net + m11_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, m12_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m12_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, m12_pf_net + m12_cpf_net, format7)

        final_col += 1
        sheet.write(final_row, final_col, cl_pf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, cl_cpf_net, format7)
        final_col += 1
        sheet.write(final_row, final_col, cl_pf_net + cl_cpf_net, format7)


        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Month Wise Employee PF Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=month.wise.employee.pf.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_pf_report_sql(self, date_from, date_to, user_work_location_id, department_id, employee_id, contribution_type):
        year = self.fiscalyear_id.name
        work_location_name = "All"
        dept_name = "All"
        filter = ""
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "emp.name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "emp.id_card_no"
        print(order_by)


        if contribution_type != 'all':
            filter = "WHERE pf.contribution_type = '%s'" % contribution_type

        if user_work_location_id:
            if filter == '':
                filter = "WHERE emp.user_work_location_id = %s" % user_work_location_id.id
            else:
                filter += " AND emp.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if department_id:
            if filter == '':
                filter = "WHERE emp.department_id = %s" % department_id.id
            else:
                filter += " AND emp.department_id = %s" % department_id.id

            dept_name = department_id.display_name

        if employee_id:
            if filter == '':
                filter = "WHERE pf.employee_id = %s" % employee_id.id
            else:
                filter += " AND pf.employee_id = %s" % employee_id.id

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            if filter == '':
                filter = "WHERE emp.sbu_unit_id = {0}".format(self.sbu_unit_id.id)  
            else:
                filter = "AND emp.sbu_unit_id = {0}".format(self.sbu_unit_id.id)  


        month_list1 = pd.period_range(start=date_from, end=date_to, freq='M')
        #month_list = [month.strftime("%Y-%m") for month in month_list1]
        month_list = []
        month_view = []
        for month in month_list1:
            month_list.append(month.strftime("%Y-%m"))
            month_view.append(month.strftime("%b'%y"))

        data_sql = """
                SELECT pf.employee_id,emp.id_card_no as emp_card,emp.name as emp_name,dept.name as dept_name,desig.name->>'en_US' as desig_name,wloc.name as wloc_name,
                emp.initial_employment_date as join_date,emp.tax_id as etin,emp.pf_start_date as pf_start_date,
                SUM(CASE WHEN CONCAT(year,'-',month) < '{0}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS op_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) < '{0}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS op_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{0}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m1_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{0}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m1_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{1}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m2_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{1}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m2_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{2}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m3_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{2}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m3_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{3}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m4_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{3}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m4_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{4}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m5_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{4}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m5_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{5}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m6_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{5}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m6_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{6}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m7_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{6}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m7_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{7}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m8_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{7}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m8_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{8}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m9_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{8}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m9_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{9}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m10_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{9}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m10_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{10}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m11_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{10}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m11_cpf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{11}' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS m12_pf,
                SUM(CASE WHEN CONCAT(year,'-',month) = '{11}' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS m12_cpf
                from hr_employee_pf pf
                LEFT JOIN hr_employee emp ON emp.id = pf.employee_id
                LEFT JOIN hr_department dept ON dept.id = emp.department_id
                LEFT JOIN hr_job desig ON desig.id = emp.job_id
                LEFT JOIN stock_location wloc ON wloc.id = emp.user_work_location_id
                {14} JOIN (
                        SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                        JOIN hr_employee_category etag on etag.id=ecr.category_id
                        {13}
                        GROUP BY emp_id
                    ) emp_tag ON emp_tag.emp_id = emp.id
                {12}
                GROUP BY pf.employee_id,emp.id_card_no, emp.name,dept.name,desig.name,wloc.name,emp.initial_employment_date,emp.tax_id,emp.pf_start_date
                ORDER BY {15}
                """.format(month_list[0], month_list[1], month_list[2], month_list[3], month_list[4],
                           month_list[5], month_list[6], month_list[7], month_list[8], month_list[9],
                           month_list[10], month_list[11],filter, tags_filter, tag_filter_join, order_by)
        self.env.cr.execute(data_sql)
        data_list = self.env.cr.dictfetchall()

        data = {
            'model': 'month.wise.employee.pf.report.wizard',
            'form': self.read()[0],
            'csr': data_list,
            'month_list': month_list,
            'month_view': month_view,
            'work_location_name': work_location_name,
            'dept_name': dept_name,
            'year': year,
            'contribution_type': contribution_type.upper(),
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }

        return data
