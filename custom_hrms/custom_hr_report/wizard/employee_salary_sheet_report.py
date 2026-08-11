from datetime import date
from calendar import monthrange
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
from datetime import datetime
from itertools import groupby

import xlsxwriter

import base64
from io import BytesIO


class EmployeeSalarySheetWizard(models.TransientModel):
    _name = "employee.salary.sheet.wizard"
    _description = "Employee Salary Sheet Wizard"

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

    file_data = fields.Binary('Employee Salary Sheet')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    include_zero_less_payable = fields.Boolean('With negative/zero payable')
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

    category_ids = fields.Many2many('hr.employee.category', 'employee_salary_sheet_employee_category_rel', 
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

    location_id = fields.Many2one('stock.location', string='Branch',default=lambda self: self._get_work_loc(), domain=lambda self: self._set_domain_work_loc())
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')

    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('Start date cannot be greater than the end date.'))

    def employee_salary_sheet_report_pdf(self):
        # year = self.year
        # month = self.month
        # location_id = self.location_id.id
        # department_id = self.department_id
        # employee_id = self.employee_id
        # state = self.state
        # include_zero_less_payable = self.include_zero_less_payable

        # get data from sql
        #data = self.employee_salary_sheet_report_sql(month, year, location_id, state, include_zero_less_payable, department_id, employee_id)
        data = self.employee_salary_sheet_report_sql()
        # data = {
        #     'ftr_id': self.id
        # }

        return self.env.ref(
            'custom_hr_report.employee_salary_sheet_report_tmpl').with_context(landscape=True).report_action(
            self, data=data)

    def employee_salary_sheet_report_excel(self):
        year = self.year
        month = self.month
        location_id = self.location_id.id
        department_id = self.department_id
        employee_id = self.employee_id
        state = self.state
        include_zero_less_payable = self.include_zero_less_payable

        # get data from sql
        #data = self.employee_salary_sheet_report_sql(month, year, location_id, state, include_zero_less_payable, department_id, employee_id)
        data = self.employee_salary_sheet_report_sql()

        file_name = "Employee Salary Sheet (%s - %s).xlsx" % (data['month'], data['year'])
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

        sheet = workbook.add_worksheet('Employee Salary Sheet')

        if location_id:
            sheet.merge_range(0, 0, 2, 18,
                              '{0}\nEmployee Salary Sheet ({1} - {2})\nBranch: {3}'.format(self.company_id.name,
                                                                                           data['month'], data['year'],
                                                                                           self.location_id.name),
                              format0)
        else:
            sheet.merge_range(0, 0, 2, 18,
                              '{0}\nEmployee Salary Sheet ({1} - {2})\nBranch: All Branches'.format(
                                  self.company_id.name, data['month'], data['year']),
                              format0)



        total_gross = 0
        total_absent = 0
        total_leave = 0
        total_ab_ded = 0
        total_att_sal = 0
        total_advance = 0
        total_loan = 0
        total_tpf = 0
        total_other_alw = 0
        total_dla = 0
        total_ota = 0
        total_no_overtime = 0
        total_other_ded = 0
        total_actual_late = 0
        total_late_ded = 0
        total_other_pay = 0

        branch_row = 3
        col = 0

        for rec in data['csr']:
            for rec2 in rec:
                sheet.merge_range(branch_row, 0, branch_row, 6,
                                  'Branch: {0}'.format(rec[rec2][0]['loc_name']), format1)

                sheet.merge_range(branch_row, 7, branch_row, 12, 
                                    'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
                sheet.merge_range(branch_row, 13, branch_row, 18,
                                    'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)


                head_row = branch_row + 1

                sheet.write(head_row, 0, 'Employee ID', format2)
                sheet.write(head_row, 1, 'Name', format1)
                # sheet.write(3, 2, 'Joining Date', format2)
                sheet.write(head_row, 2, 'Gross Salary', format3)
                sheet.write(head_row, 3, 'Absent', format2)
                sheet.write(head_row, 4, 'Leave', format2)
                sheet.write(head_row, 5, 'Absent Deduct', format3)
                sheet.write(head_row, 6, 'Att. Salary', format3)
                sheet.write(head_row, 7, 'Advance Deduct', format3)
                sheet.write(head_row, 8, 'Loan Deduct', format3)
                sheet.write(head_row, 9, 'TPF Deduct', format3)
                sheet.write(head_row, 10, 'Additional Allowance', format3)
                sheet.write(head_row, 11, 'OT Days', format3)
                sheet.write(head_row, 12, 'OT Amount', format3)
                sheet.write(head_row, 13, 'Daily Allowance', format3)
                sheet.write(head_row, 14, 'Other Deduction', format3)
                sheet.write(head_row, 15, 'Actual Late Days', format3)
                sheet.write(head_row, 16, 'Late Deduction', format3)
                sheet.write(head_row, 17, 'Payable Salary', format3)
                sheet.write(head_row, 18, 'Signature', format1)

                body_row = head_row + 1

                for rec3 in rec[rec2]:

                    sheet.write(body_row, col, rec3['id_card'], format5)
                    if rec3['des_name']:
                        sheet.write(body_row, col + 1, '{0} ({1})'.format(rec3['employee_name'], rec3['des_name']), format4)
                    else:
                        sheet.write(body_row, col + 1, rec3['employee_name'], format4)

                    # joining_date = datetime.strptime(str(rec3['joining_date']), '%Y-%m-%d').strftime('%d-%b-%Y') if rec3['joining_date'] else None
                    # sheet.write(body_row, col + 2, joining_date, format5)
                    sheet.write(body_row, col + 2, round(rec3['gross_salary'], 2), format6)
                    total_gross = total_gross + rec3['gross_salary']

                    sheet.write(body_row, col + 3, round(rec3['no_abs'], 0), format5)
                    total_absent = total_absent + rec3['no_abs']

                    sheet.write(body_row, col + 4, round(rec3['no_leave'], 0), format5)
                    total_leave = total_leave + rec3['no_leave']

                    sheet.write(body_row, col + 5, round(rec3['ab_amt'], 2), format6)
                    total_ab_ded = total_ab_ded + rec3['ab_amt']

                    sheet.write(body_row, col + 6, round(rec3['gross_salary'] - rec3['ab_amt'], 2), format6)
                    total_att_sal = total_att_sal + (rec3['gross_salary'] - rec3['ab_amt'])

                    sheet.write(body_row, col + 7, round(rec3['adv_salary'], 2), format6)
                    total_advance = total_advance + rec3['adv_salary']

                    sheet.write(body_row, col + 8, round(rec3['loan'], 2), format6)
                    total_loan = total_loan + rec3['loan']

                    sheet.write(body_row, col + 9, round(rec3['tpf'], 2), format6)
                    total_tpf = total_tpf + rec3['tpf']

                    sheet.write(body_row, col + 10, round(rec3['other_alw'], 2), format6)
                    total_other_alw = total_other_alw + rec3['other_alw']

                    sheet.write(body_row, col + 11, round(rec3['no_overtime'], 0), format6)
                    total_no_overtime = total_no_overtime + rec3['no_overtime']

                    sheet.write(body_row, col + 12, round(rec3['ota'], 2), format6)
                    total_ota = total_ota + rec3['ota']

                    sheet.write(body_row, col + 13, round(rec3['dla'], 2), format6)
                    total_dla = total_dla + rec3['dla']

                    sheet.write(body_row, col + 14, round(rec3['other_ded'], 2), format6)
                    total_other_ded = total_other_ded + rec3['other_ded']

                    sheet.write(body_row, col + 15, round(rec3['actual_late'], 0), format6)
                    total_actual_late = total_actual_late + rec3['actual_late']

                    sheet.write(body_row, col + 16, round(rec3['late_ded'], 2), format6)
                    total_late_ded = total_late_ded + rec3['late_ded']

                    sheet.write(body_row, col + 17, round(rec3['total_payable_sal'], 2), format6)
                    total_other_pay = total_other_pay + rec3['total_payable_sal']
                    sheet.write(body_row, col + 18, '', format5)

                    body_row = body_row + 1

            final_row = body_row
            final_col = 0
            sheet.merge_range(final_row, final_col, final_row, final_col + 1, 'Total', format7)
            sheet.write(final_row, final_col + 2, round(total_gross, 2), format7)
            sheet.write(final_row, final_col + 3, round(total_absent, 2), format9)
            sheet.write(final_row, final_col + 4, round(total_leave, 2), format9)
            sheet.write(final_row, final_col + 5, round(total_ab_ded, 2), format7)
            sheet.write(final_row, final_col + 6, round(total_att_sal, 2), format7)
            sheet.write(final_row, final_col + 7, round(total_advance, 2), format7)
            sheet.write(final_row, final_col + 8, round(total_loan, 2), format7)
            sheet.write(final_row, final_col + 9, round(total_tpf, 2), format7)
            sheet.write(final_row, final_col + 10, round(total_other_alw, 2), format7)
            sheet.write(final_row, final_col + 11, round(total_no_overtime, 2), format7)
            sheet.write(final_row, final_col + 12, round(total_ota, 2), format7)
            sheet.write(final_row, final_col + 13, round(total_dla, 2), format7)
            sheet.write(final_row, final_col + 14, round(total_other_ded, 2), format7)
            sheet.write(final_row, final_col + 15, round(total_actual_late, 2), format7)
            sheet.write(final_row, final_col + 16, round(total_late_ded, 2), format7)
            sheet.write(final_row, final_col + 17, round(total_other_pay, 2), format7)
            sheet.write(final_row, final_col + 18, '', format9)

            total_gross = 0
            total_absent = 0
            total_leave = 0
            total_ab_ded = 0
            total_att_sal = 0
            total_advance = 0
            total_loan = 0
            total_tpf = 0
            total_other_alw = 0
            total_dla = 0
            total_ota = 0
            total_no_overtime = 0
            total_other_ded = 0
            total_actual_late = 0
            total_late_ded = 0
            total_other_pay = 0

            branch_row = final_row + 2

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Salary Sheet',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.salary.sheet.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_salary_sheet_report_sql(self):
        month = self.month
        year = self.year
        location_id = self.location_id
        state = self.state
        include_zero_less_payable = self.include_zero_less_payable
        department_id = self.department_id
        employee_id = self.employee_id

        m = int(month)
        y = int(year)
        ndays = monthrange(y, m)[1]
        start_date = date(y, m, 1)
        state = state
        end_date = date(y, m, ndays)
        include_non_zero_payable_filter = ""

        locationFilter = ""
        if location_id:
            locationFilter = "AND hp.user_work_location_id = %s" % (location_id.id)

        dept_filter = ""
        dept_filter2 = ""
        emp_filter = ""
        dept_name = "All"
        emp_name = "All"
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "mtbl.employee_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "mtbl.id_card"
        # print(order_by)

        if department_id:
            dept_filter = "WHERE tbl1.dept_id = %s" % department_id.id
            dept_filter2 = "AND hp.department_id = %s" % department_id.id
            dept_name = department_id.display_name
        if employee_id:
            emp_filter = "AND hre.id = %s" % employee_id.id
            emp_name = employee_id.display_name

        if not include_zero_less_payable:
            include_non_zero_payable_filter = "WHERE tbl1.total_payable_sal > 0"

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND hre.sbu_unit_id = {0}".format(self.sbu_unit_id.id) 

        data_sql = """ SELECT mtbl.emp_id, mtbl.employee_name, mtbl.des_name, stl.name AS loc_name, COALESCE(mtbl.user_work_location_id, 10000) AS user_work_location_id, mtbl.joining_date, mtbl.id_card, 
                        COALESCE(SUM(mtbl.gross_salary), 0) AS gross_salary,
                        COALESCE(SUM(mtbl.no_abs), 0) AS no_abs,
                        COALESCE(SUM(mtbl.no_leave), 0) AS no_leave,
                        COALESCE(SUM(mtbl.actual_late), 0) AS actual_late,
                        COALESCE(SUM(mtbl.no_overtime), 0) AS no_overtime,
                        COALESCE(SUM(mtbl.basic_salary), 0) AS basic_salary,
                        COALESCE(SUM(mtbl.adv_salary), 0) AS adv_salary,
                        COALESCE(SUM(mtbl.ab_amt),0) AS ab_amt,
                        COALESCE(SUM(mtbl.loan),0) AS loan,
                        COALESCE(SUM(mtbl.tpf), 0) AS tpf,
                        COALESCE(SUM(mtbl.other_alw),0) AS other_alw,
                        COALESCE(SUM(mtbl.dla),0) AS dla,
                        COALESCE(SUM(mtbl.ota),0) AS ota,
                        COALESCE(SUM(mtbl.other_ded),0) AS other_ded,
                        COALESCE(SUM(mtbl.late_ded),0) AS late_ded,
                        COALESCE(SUM(mtbl.total_payable_sal),0) AS total_payable_sal
                        FROM (
                            SELECT tbl1.emp_id, tbl1.employee_name,tbl1.user_work_location_id, tbl1.des_name, tbl1.joining_date, tbl1.id_card,
                            COALESCE(SUM(tbl1.gross_salary), 0) AS gross_salary,
                            COALESCE(SUM(tbl1.basic_salary), 0) AS basic_salary,
                            COALESCE(SUM(tbl1.adv_salary), 0) AS adv_salary,
                            COALESCE(SUM(tbl1.ab_amt),0) AS ab_amt,
                            COALESCE(SUM(tbl1.loan),0) AS loan,
                            COALESCE(SUM(tbl1.tpf), 0) AS tpf,
                            COALESCE(SUM(tbl1.other_alw),0) AS other_alw,
                            COALESCE(SUM(tbl1.dla),0) AS dla,
                            COALESCE(SUM(tbl1.ota),0) AS ota,
                            COALESCE(SUM(tbl1.other_ded),0) AS other_ded,
                            COALESCE(SUM(tbl1.late_ded),0) AS late_ded,
                            COALESCE(SUM(tbl1.total_payable_sal),0) AS total_payable_sal,
                            COALESCE(SUM(tbl2.no_absence), 0) AS no_abs,
                            COALESCE(SUM(tbl2.no_leave), 0) AS no_leave,
                            COALESCE(SUM(tbl2.actual_late), 0) AS actual_late,
                            COALESCE(SUM(tbl2.no_overtime), 0) AS no_overtime
                            
                            FROM(
                            SELECT hre.id AS emp_id, hre.name AS employee_name,hre.user_work_location_id as user_work_location_id,hj.name->>'en_US' AS des_name, DATE(hre.initial_employment_date) AS joining_date, hre.id_card_no as id_card,
                                --SUM(COALESCE(atts.no_absence, 0)) AS no_abs,
                                --SUM(COALESCE((atts.no_cl+atts.no_ml+atts.no_pl), 0)) AS no_leave,
                                --SUM(COALESCE(atts.actual_late_count, 0)) AS actual_late,
                                --SUM(COALESCE(atts.no_overtime, 0)) AS no_overtime,
                                SUM(CASE WHEN hpl.code = 'BASIC' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS basic_salary,
                                SUM(CASE WHEN hpl.code = 'GROSS' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS gross_salary,
                                SUM(CASE WHEN hpl.code = 'SAR' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS adv_salary,
                                SUM(CASE WHEN hpl.code = 'ABS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS ab_amt,
                                SUM(CASE WHEN hpl.code in ('LOANINS', 'LOANINT') THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS loan,
                                SUM(CASE WHEN hpl.code = 'PF' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS tpf,
                                SUM(CASE WHEN (hplc.code = 'ALW' AND hsr.is_other = True) THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS other_alw,
                                SUM(CASE WHEN hpl.code = 'DLA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS dla,
                                SUM(CASE WHEN hpl.code in ('OT','OVT','OTA') THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS ota,
                                SUM(CASE WHEN (hplc.code = 'DED' AND hsr.is_other = True) THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS other_ded,
                                SUM(CASE WHEN hpl.code = 'LATE' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS late_ded,
                                SUM(CASE WHEN hpl.code = 'NET' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS total_payable_sal
                                FROM hr_employee hre
                                JOIN hr_payslip hp ON hp.employee_id = hre.id
                                JOIN hr_payslip_line hpl ON hpl.slip_id = hp.id
                                LEFT JOIN hr_salary_rule_category hplc ON hpl.category_id = hplc.id
                                LEFT JOIN hr_job hj ON hj.id = hre.job_id
                                LEFT JOIN hr_salary_rule hsr ON hsr.id = hpl.salary_rule_id
                                --LEFT JOIN (SELECT * FROM attendance_sheet WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}') atts ON atts.employee_id = hre.id
                                LEFT JOIN hr_payroll_structure hps ON hps.id = hp.struct_id       
                                {9} JOIN (
                                        SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                        JOIN hr_employee_category etag on etag.id=ecr.category_id
                                        {8}
                                        GROUP BY emp_id
                                    ) emp_tag ON emp_tag.emp_id = hre.id                 
                                WHERE hps.code = 'BASE' AND DATE(hp.date_to) BETWEEN '{0}' AND '{1}'
                                AND hp.state = '{3}'
                                {2} {5} {6} {7}
                                GROUP BY hre.id, hre.name, hj.name, hre.initial_employment_date, hre.id_card_no
                                ORDER BY hre.name
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
                                        SUM(COALESCE((no_cl+no_ml+no_pl), 0)) AS no_leave,
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
                                
                            --LEFT JOIN (
                                --SELECT employee_id, COALESCE(SUM(number_of_days), 0) AS no_leave
                                --FROM hr_leave
                                --WHERE state = 'validate' AND DATE(request_date_to) BETWEEN '{0}' AND '{1}'
                                --GROUP BY employee_id
                            --) tbl2 ON tbl2.employee_id = tbl1.emp_id
                            
                            {4}
                            GROUP BY tbl1.emp_id, tbl1.employee_name, tbl1.des_name, tbl1.joining_date, tbl1.id_card,tbl1.user_work_location_id
                            ORDER BY tbl1.employee_name
                        ) mtbl
                        LEFT JOIN stock_location stl ON stl.id = mtbl.user_work_location_id
                        GROUP BY mtbl.emp_id, mtbl.employee_name,mtbl.user_work_location_id, mtbl.des_name, mtbl.joining_date, mtbl.id_card,stl.name
                        -- ORDER BY stl.name, mtbl.id_card, mtbl.employee_name
                        ORDER BY stl.name, {10}, mtbl.employee_name
                    """.format(start_date, end_date,
                                locationFilter, state, 
                                include_non_zero_payable_filter, dept_filter2, 
                                emp_filter, business_unit_filter,
                                tags_filter, tag_filter_join,
                                order_by)

        #print('data_sql----', data_sql)

        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        # print(data_res)

        # define a fuction for key
        def key_func(k):
            return k['user_work_location_id']

        data_res = sorted(data_res, key=key_func)

        data_list = []

        for key, value in groupby(data_res, key_func):
            vals = {
                key: list(value)
            }
            data_list.append(vals)

        report_color_obj = self.env['report.color.settings'].search([('report_name', '=', '02')], limit=1)

        if report_color_obj.color1:
            color1 = report_color_obj.color1 if report_color_obj.color1.startswith("#") else '#' + report_color_obj.color1
        else:
            color1 = '#FFFFFF'
        if report_color_obj.color2:
            color2 = report_color_obj.color2 if report_color_obj.color2.startswith("#") else '#' + report_color_obj.color2
        else:
            color2 = '#FFFFFF'
        if report_color_obj.color3:
            color3 = report_color_obj.color3 if report_color_obj.color3.startswith("#") else '#' + report_color_obj.color3
        else:
            color3 = '#FFFFFF'

        data = {
            'model': "employee.salary.sheet.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'month': dict(self._fields['month'].selection).get(self.month),
            'color1': color1,
            'color2': color2,
            'color3': color3,
            'dept_name': dept_name,
            'emp_name': emp_name,
            'year': year,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data
