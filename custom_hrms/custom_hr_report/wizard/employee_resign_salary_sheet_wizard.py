from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from calendar import monthrange
from datetime import date
import datetime
from datetime import datetime
import xlsxwriter

import base64
from io import BytesIO


class EmployeeResignSalarySheetWizard(models.TransientModel):
    _name = "employee.resign.salary.sheet.wizard"
    _description = "Employee Resign Salary Sheet Wizard"

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

    file_data = fields.Binary('Employee Resign Salary Sheet Wizard')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
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
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    category_ids = fields.Many2many('hr.employee.category', 'employee_resign_salary_sheet_employee_category_rel', 
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

    def employee_resign_salary_sheet_pdf(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        state = self.state
        user_work_location_id = self.user_work_location_id
        # get data from sql
        data = self.employee_resign_salary_sheet_sql(month, year, department_id, state, user_work_location_id)

        return self.env.ref(
            'custom_hr_report.employee_resign_salary_sheet_tmpl').with_context(landscape=True).report_action(
            self,
            data=data)

    def employee_resign_salary_sheet_excel(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        state = self.state
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.employee_resign_salary_sheet_sql(month, year, department_id, state, user_work_location_id)

        file_name = "Employee Resign Salary Sheet (%s - %s).xlsx" % (data['month'], data['year'])
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

        sheet = workbook.add_worksheet('Employee Resign Salary Sheet')

        sheet.merge_range(0, 0, 0, 28, "{0}".format(data['form']['company_id'][1]), format0)
        sheet.merge_range(1, 0, 2, 28,
                          "Employee Resign Salary Sheet (%s - %s)" % (data['month'], data['year']),
                          format0)

        sheet.merge_range(3, 0, 3, 5, 'Work/Job Location: {0}'.format(data['work_loc_name']), format1)
        sheet.merge_range(3, 6, 3, 11, 'Status: {0}'.format(data['state_name']), format2)
        sheet.merge_range(3, 12, 3, 17, 'Department Name: {0}'.format(data['dept_name']), format2)
        sheet.merge_range(3, 18, 3, 23, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format2)
        sheet.merge_range(3, 24, 3, 28, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format3)

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
        sheet.write(5, 10, 'Medical', format3)
        sheet.write(5, 11, 'Con. Allowance', format3)
        sheet.write(5, 12, 'Gross Salary', format3)
        sheet.merge_range(4, 13, 4, 18, '', format2)
        sheet.write(5, 13, 'Holy Day(Friday + Occasion)', format2)
        sheet.write(5, 14, 'Leave', format2)
        sheet.write(5, 15, 'Absent Day', format2)
        sheet.write(5, 16, 'Total Present Day', format2)
        sheet.write(5, 17, 'Day of Month', format2)
        sheet.write(5, 18, 'Absent Amount', format2)
        sheet.merge_range(4, 19, 4, 24, 'Deduct', format2)
        sheet.write(5, 19, 'Accrued Salary Payable', format3)
        sheet.write(5, 20, 'Tax', format2)
        sheet.write(5, 21, 'Advance Amount', format3)
        sheet.write(5, 22, 'Loan Adjustment', format3)
        sheet.write(5, 23, 'PF', format3)
        sheet.write(5, 24, 'Stamp', format2)
        sheet.merge_range(4, 25, 5, 25, 'Cash Payment', format3)
        sheet.merge_range(4, 26, 5, 26, 'Bank Payment', format3)
        sheet.merge_range(4, 27, 5, 27, 'Adjusted', format2)
        sheet.merge_range(4, 28, 5, 28, 'Signature', format2)

        row = 6
        col = 0

        sl_no = 1

        for rec in data['csr']:
            sheet.write(row, col + 0, sl_no, format5)
            sheet.write(row, col + 1, rec['id_card_no'], format5)
            sheet.write(row, col + 2, rec['employee_name'], format4)
            joining_date = datetime.strptime(str(rec['joining_date']), '%Y-%m-%d').strftime('%d-%b-%Y') if rec[
                'joining_date'] else None
            sheet.write(row, col + 3, joining_date, format5)
            sheet.write(row, col + 4, rec['dept_name'], format4)
            sheet.write(row, col + 5, rec['emp_designation'], format4)
            sheet.write(row, col + 6, rec['bnk_ac'], format4)
            sheet.write(row, col + 7, rec['emp_work_location'], format4)
            sheet.write(row, col + 8, round(rec['basic_salary'], 2), format6)
            sheet.write(row, col + 9, round(rec['house_rent'], 2), format6)
            sheet.write(row, col + 10, round(rec['medical_alw'], 2), format6)
            sheet.write(row, col + 11, round(rec['conv_alw'], 2), format6)
            sheet.write(row, col + 12, round(rec['gross_salary'], 2), format6)
            sheet.write(row, col + 13, rec['holy_day'], format5)
            sheet.write(row, col + 14, rec['leave'], format5)
            sheet.write(row, col + 15, rec['abs_day'], format5)
            sheet.write(row, col + 16, rec['present_day'], format5)
            sheet.write(row, col + 17, rec['total_day_of_month'], format5)
            sheet.write(row, col + 18, round(rec['abs_amt'], 2), format5)
            sheet.write(row, col + 19, round(rec['payable_salary'], 2), format6)
            # sheet.write(row, col + 20, round(rec['tds'], 2), format5)
            sheet.write(row, col + 20, round(rec.get('tds', 0) or 0, 2), format5)
            sheet.write(row, col + 21, round(rec['advance_amount'], 2), format6)
            sheet.write(row, col + 22, round(rec['loan_adj'], 2), format6)
            sheet.write(row, col + 23, round(rec['pf'], 2), format6)
            sheet.write(row, col + 24, round(rec.get('stamp', 0) or 0, 2), format5)
            sheet.write(row, col + 25, round(rec.get('cash_pay', 0) or 0, 2), format6)
            sheet.write(row, col + 26, round(rec.get('bank_pay', 0) or 0, 2), format6)

            sheet.write(row, col + 27, None, format5)
            sheet.write(row, col + 28, None, format5)

            row = row + 1
            sl_no = sl_no + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Resign Salary Sheet',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.resign.salary.sheet.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_resign_salary_sheet_sql(self, month, year, department_id, state, user_work_location_id):
        m = int(month)
        y = int(year)
        ndays = monthrange(y, m)[1]
        start_date = date(y, m, 1)
        end_date = date(y, m, ndays)

        state_filter = ""
        dept_filter = ""
        work_loc_filter = ""
        state_name = ""
        dept_name = "All"
        work_location_name = "All"
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "tbl1.emp_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "tbl1.emp_id_card"
        print(order_by)

        if state:
            state_filter = "AND hp.state = '%s'" % state
            state_name = dict(self._fields['state'].selection).get(self.state)

        if department_id:
            dept_filter = "WHERE tbl1.dept_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            work_loc_filter = "AND hp.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND he.sbu_unit_id = {0}".format(self.sbu_unit_id.id) 

        data_sql = """
                    SELECT tbl1.emp_id, tbl1.emp_name, tbl1.emp_id_card, tbl1.emp_joining_date, tbl1.dept_id, tbl1.des_id, tbl1.work_loc_id, tbl1.bank_ac, COALESCE(SUM(tbl1.basic), 0) AS basic, COALESCE(SUM(tbl1.house_rent), 0) AS house_rent,
                COALESCE(SUM(tbl1.medical_alw), 0) AS medical_alw, COALESCE(SUM(tbl1.con_alw), 0) AS con_alw, COALESCE(SUM(tbl1.gross), 0) AS gross, COALESCE(SUM(tbl2.holy_day), 0) AS holy_day, COALESCE(SUM(tbl1.tpf), 0) AS tpf,
                COALESCE(SUM(tbl1.no_of_leave), 0) AS no_of_leave, COALESCE(SUM(tbl1.absent_day), 0) AS absent_day, COALESCE(SUM(tbl1.present_day),0) AS present_day, COALESCE(SUM(tbl1.day_of_month),0) AS day_of_month,
                COALESCE(SUM(tbl1.ab_amt), 0) AS ab_amt, COALESCE(SUM(tbl1.total_payable_sal), 0) AS total_payable_sal, COALESCE(SUM(tbl1.adv_salary),0) AS adv_salary, COALESCE(SUM(tbl1.loan),0) AS loan, COALESCE(SUM(tbl1.tds),0) AS tds,
                COALESCE(SUM(tbl1.stamp), 0) AS stamp, COALESCE(SUM(tbl1.bank_pay), 0) AS bank_pay, COALESCE(SUM(tbl1.cash_pay), 0) AS cash_pay
                FROM(
                    SELECT he.id AS emp_id, he.name AS emp_name, he.id_card_no AS emp_id_card, he.initial_employment_date AS emp_joining_date, hp.department_id AS dept_id, he.job_id AS des_id, he.s_bank_account_no as bank_ac,
                    hp.user_work_location_id AS work_loc_id, 
                    --hc.wage AS basic, hc.hra AS house_rent, hc.medical_allowance AS medical_alw, hc.travel_allowance AS con_alw, hc.gross_salary AS gross, 
                    hl.number_of_days AS no_of_leave, ast.no_absence AS absent_day, ast.no_presence AS present_day, ast.no_of_days AS day_of_month,
                    
                    SUM(CASE WHEN hpl.code = 'BASIC' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS basic,
                    SUM(CASE WHEN hpl.code = 'HRA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS house_rent,
                    SUM(CASE WHEN hpl.code = 'MEDICAL' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS medical_alw,
                    SUM(CASE WHEN hpl.code = 'TA' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS con_alw,
                    SUM(CASE WHEN hpl.code = 'GROSS' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS gross,
                    SUM(CASE WHEN hpl.code = 'ABS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS ab_amt,
                    SUM(CASE WHEN hpl.code = 'NET' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS total_payable_sal,
                    SUM(CASE WHEN hpl.code = 'SAR' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS adv_salary,
                    SUM(CASE WHEN hpl.code in ('LOANINS', 'LOANINT') THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS loan,
                    SUM(CASE WHEN hpl.code = 'PF' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS tpf,
                    SUM(CASE WHEN hpl.code = 'TDS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS tds,
                    SUM(CASE WHEN hpl.code = 'STMP' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS stamp,
                    hp.bank_amount AS bank_pay, hp.cash_amount AS cash_pay
                    FROM hr_employee he
                    --LEFT JOIN hr_contract hc ON hc.employee_id = he.id
                    LEFT JOIN (SELECT * FROM attendance_sheet WHERE state='done' AND DATE(date_to) BETWEEN '{0}' AND '{1}') ast ON ast.employee_id = he.id
                    LEFT JOIN hr_leave hl ON hl.employee_id = he.id
                    LEFT JOIN hr_payslip hp ON hp.employee_id = he.id
                    LEFT JOIN hr_payslip_line hpl ON hpl.slip_id = hp.id
                    LEFT JOIN hr_payroll_structure hps ON hps.id = hp.struct_id  
                    {7} JOIN (
                            SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                            JOIN hr_employee_category etag on etag.id=ecr.category_id
                            {6}
                            GROUP BY emp_id
                        ) emp_tag ON emp_tag.emp_id = he.id
                    WHERE hps.code = 'BASE' AND DATE(hp.date_to) BETWEEN '{0}' AND '{1}' {2} AND he.id IN (SELECT employee_id FROM hr_resignation WHERE state='approved' AND DATE(expected_revealing_date) BETWEEN '{0}' AND '{1}')
                    {4} {5}
                    --AND hc.state = 'close' 
                    GROUP BY he.id, he.name, he.id_card_no, he.initial_employment_date, hp.department_id , he.s_bank_account_no, he.job_id, hp.user_work_location_id,hp.bank_amount,hp.cash_amount, hl.number_of_days, ast.no_absence, ast.no_presence, ast.no_of_days
                    --hc.wage , hc.hra, hc.medical_allowance, hc.travel_allowance, hc.gross_salary,
                    ) tbl1
                    LEFT JOIN (
                        SELECT ast.employee_id, COUNT(astl.id) AS holy_day
                        FROM attendance_sheet ast
                        LEFT JOIN attendance_sheet_line astl ON astl.att_sheet_id = ast.id
                        WHERE astl.status in ('ph', 'weekend') AND ast.employee_id IN (SELECT employee_id FROM hr_resignation WHERE state='approved' AND DATE(expected_revealing_date) BETWEEN '{0}' AND '{1}')
                        AND ast.state='done' AND DATE(ast.date_to) BETWEEN '{0}' AND '{1}'
                        GROUP BY ast.employee_id
                 ) tbl2 ON tbl2.employee_id = tbl1.emp_id
                 {3}
                GROUP BY tbl1.emp_id, tbl1.emp_name, tbl1.emp_id_card, tbl1.emp_joining_date, tbl1.dept_id, tbl1.des_id, tbl1.work_loc_id, tbl1.basic, tbl1.house_rent, tbl1.medical_alw, tbl1.con_alw, tbl1.gross, tbl1.bank_ac,
                tbl1.no_of_leave, tbl1.absent_day, tbl1.present_day, tbl1.day_of_month
                -- ORDER BY tbl1.emp_id_card, tbl1.emp_name
                ORDER BY {8}, tbl1.emp_name
        
        """.format(start_date, end_date,
                    state_filter, dept_filter, 
                    work_loc_filter, business_unit_filter,
                    tags_filter, tag_filter_join,
                    order_by)

        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()
        data_list = []

        for d in data_res:
            vals = {
                'id_card_no': d['emp_id_card'],
                'employee_name': d['emp_name'],
                'joining_date': d['emp_joining_date'],
                'dept_name': self.env['hr.department'].browse(d['dept_id']).display_name,
                'emp_designation': self.env['hr.job'].browse(d['des_id']).display_name,
                'bnk_ac': d['bank_ac'],
                'emp_work_location': self.env['stock.location'].browse(d['work_loc_id']).display_name,
                'basic_salary': d['basic'],
                'house_rent': d['house_rent'],
                'medical_alw': d['medical_alw'],
                'conv_alw': d['con_alw'],
                'gross_salary': d['gross'],
                'holy_day': d['holy_day'],
                'leave': d['no_of_leave'],
                'abs_day': d['absent_day'],
                'present_day': d['present_day'],
                'total_day_of_month': d['day_of_month'],
                'abs_amt': d['ab_amt'],
                'payable_salary': d['total_payable_sal'],
                'advance_amount': d['adv_salary'],
                'loan_adj': d['loan'],
                'pf': d['tpf'],
            }
            data_list.append(vals)

        data = {
            'model': "employee.detail.salary.sheet.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'month': dict(self._fields['month'].selection).get(self.month),
            'year': year,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'state_name': state_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
            
        }
        return data
