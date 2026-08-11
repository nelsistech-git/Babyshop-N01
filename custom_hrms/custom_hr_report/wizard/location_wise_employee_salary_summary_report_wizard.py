from odoo import fields, models, api
from calendar import monthrange
from datetime import date
import datetime
from datetime import datetime
import xlsxwriter

import base64
from io import BytesIO


class LocationWiseEmployeeSalarySheetReportWizard(models.TransientModel):
    _name = "location.wise.employee.salary.sheet.report.wizard"
    _description = "Location wise Employee Salary Summary Report"

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

    file_data = fields.Binary('Location wise Employee Salary Summary Report')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
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
    include_zero_less_payable = fields.Boolean('With negative/zero payable')

    category_ids = fields.Many2many('hr.employee.category', 'location_wise_employee_salary_sheet_employee_category_rel', 
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

    def location_wise_employee_salary_summary_report_excel(self):
        year = self.year
        month = self.month
        state = self.state
        user_work_location_id = self.user_work_location_id
        include_zero_less_payable = self.include_zero_less_payable

        # get data from sql
        data = self.location_wise_employee_salary_summary_report_sql(month, year, state, user_work_location_id, include_zero_less_payable)

        file_name = "Location wise Employee Salary Sheet Report (%s - %s).xlsx" % (data['month'], data['year'])
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

        sheet = workbook.add_worksheet('Location wise Employee Salary Sheet Report')

        sheet.merge_range(0, 0, 0, 9, "{0}".format(data['form']['company_id'][1]), format0)

        sheet.merge_range(0, 0, 2, 12,
                          "Location wise Employee Salary Sheet Report (%s - %s)" % (data['month'], data['year']),
                          format0)

        sheet.merge_range(3, 0, 3, 3, 'Status: {0}'.format(data['state_name']), format1)
        sheet.merge_range(3, 4, 3, 8, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
        sheet.merge_range(3, 9, 3, 12, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)


        sheet.write(4, 0, 'Sl.', format2)
        sheet.write(4, 1, 'Location', format1)
        sheet.write(4, 2, 'Total Employee', format2)
        sheet.write(4, 3, 'Gross Salary', format3)
        sheet.write(4, 4, 'Absent Deduct', format3)
        sheet.write(4, 5, 'Payable Amount', format3)
        sheet.write(4, 6, 'Advance Amount', format3)
        sheet.write(4, 7, 'Loan Adjustment', format3)
        sheet.write(4, 8, 'Tax', format2)
        sheet.write(4, 9, 'Provident Fund', format3)
        sheet.write(4, 10, 'Stamp', format2)
        sheet.write(4, 11, 'Net Payable(Cash)', format2)
        sheet.write(4, 12, 'Net Payable(Bank)', format2)

        row = 5
        col = 0

        sl_no = 1
        t_emp = 0
        t_gross = 0
        t_abs_amt = 0
        t_payable_salary = 0
        t_advance_salary = 0
        t_loan_adj = 0
        t_pf = 0
        t_tds = 0
        t_cash_pay = 0
        t_bank_pay = 0
        t_stamp = 0

        for rec in data['csr']:
            sheet.write(row, col + 0, sl_no, format5)
            sheet.write(row, col + 1, rec['loc_name'], format4)
            sheet.write(row, col + 2, rec['emp_count'], format5)
            t_emp = t_emp + rec['emp_count']
            sheet.write(row, col + 3, round(rec['gross_salary'], 2), format6)
            t_gross = t_gross + rec['gross_salary']
            sheet.write(row, col + 4, round(rec['abs_amt'], 2), format6)
            t_abs_amt = t_abs_amt + rec['abs_amt']
            sheet.write(row, col + 5, round(rec['payable_salary'], 2), format6)
            t_payable_salary = t_payable_salary + rec['payable_salary']
            sheet.write(row, col + 6, round(rec['advance_amount'], 2), format6)
            t_advance_salary = t_advance_salary + rec['advance_amount']
            sheet.write(row, col + 7, round(rec['loan_adj'], 2), format6)
            t_loan_adj = t_loan_adj + rec['loan_adj']
            sheet.write(row, col + 8, round(rec['tds'], 2), format5)
            t_tds = t_tds + rec['tds']

            sheet.write(row, col + 9, round(rec['pf'], 2), format6)
            t_pf = t_pf + rec['pf']
            sheet.write(row, col + 10, round(rec['stamp'], 2), format5)
            t_stamp = t_stamp + rec['stamp']
            sheet.write(row, col + 11, round(rec['cash_pay'], 2), format5)
            t_cash_pay = t_cash_pay + rec['cash_pay']
            sheet.write(row, col + 12, round(rec['bank_pay'], 2), format5)
            t_bank_pay = t_bank_pay + rec['bank_pay']

            row = row + 1
            sl_no = sl_no + 1

        final_row = row
        final_col = 0
        sheet.merge_range(final_row, final_col, final_row, final_col + 1, 'Total', format7)
        sheet.write(final_row, final_col + 2, round(t_emp, 2), format9)
        sheet.write(final_row, final_col + 3, round(t_gross, 2), format7)
        sheet.write(final_row, final_col + 4, round(t_abs_amt, 2), format7)
        sheet.write(final_row, final_col + 5, round(t_payable_salary, 2), format7)
        sheet.write(final_row, final_col + 6, round(t_advance_salary, 2), format7)
        sheet.write(final_row, final_col + 7, round(t_loan_adj, 2), format7)
        sheet.write(row, col + 8, round(t_tds, 2), format9)
        sheet.write(final_row, final_col + 9, round(t_pf, 2), format7)
        sheet.write(row, col + 10, round(t_stamp, 2), format9)
        sheet.write(row, col + 11, round(t_cash_pay, 2), format9)
        sheet.write(row, col + 12, round(t_bank_pay, 2), format9)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Location wise Employee Salary Sheet Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=location.wise.employee.salary.sheet.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def location_wise_employee_salary_summary_report_pdf(self):
        year = self.year
        month = self.month
        state = self.state
        user_work_location_id = self.user_work_location_id
        include_zero_less_payable = self.include_zero_less_payable

        # get data from sql
        data = self.location_wise_employee_salary_summary_report_sql(month, year, state, user_work_location_id, include_zero_less_payable)
        return self.env.ref('custom_hr_report.location_wise_employee_details_salary_sheet_report_tmpl').with_context(
            landscape=True).report_action(self, data=data)

    def location_wise_employee_salary_summary_report_sql(self, month, year, state, user_work_location_id, include_zero_less_payable):
        m = int(month)
        y = int(year)
        ndays = monthrange(y, m)[1]
        start_date = date(y, m, 1)
        end_date = date(y, m, ndays)

        work_loc_filter = ""
        state_filter = ""
        state_name = ""
        work_location_name = "All"
        include_non_zero_payable_filter = ""

        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        if state:
            state_filter = "AND hp.state = '%s'" % state
            state_name = dict(self._fields['state'].selection).get(self.state)

        if user_work_location_id:
            work_loc_filter = "AND hp.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if not include_zero_less_payable:
            include_non_zero_payable_filter = "AND (hp.cash_amount > 0 OR hp.bank_amount > 0)"

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND he.sbu_unit_id = {0}".format(self.sbu_unit_id.id)  

        data_sql = """
                    SELECT sl.name AS loc_name, main_tbl.emp_count AS emp_count, COALESCE(SUM(main_tbl.basic), 0) AS basic, COALESCE(SUM(main_tbl.house_rent), 0) AS house_rent,
                        COALESCE(SUM(main_tbl.medical_alw), 0) AS medical_alw, COALESCE(SUM(main_tbl.con_alw), 0) AS con_alw, COALESCE(SUM(main_tbl.gross), 0) AS gross_salary,
                        COALESCE(SUM(main_tbl.holy_day), 0) AS holy_day, COALESCE(SUM(main_tbl.tpf), 0) AS pf,
                        COALESCE(SUM(main_tbl.absent_day), 0) AS absent_day, COALESCE(SUM(main_tbl.present_day),0) AS present_day, COALESCE(SUM(main_tbl.day_of_month),0) AS day_of_month,
                        COALESCE(SUM(main_tbl.ab_amt), 0) AS abs_amt, COALESCE(SUM(main_tbl.total_payable_sal), 0) AS payable_salary, COALESCE(SUM(main_tbl.adv_salary),0) AS advance_amount,
                        COALESCE(SUM(main_tbl.loan),0) AS loan_adj, COALESCE(SUM(main_tbl.tds),0) AS tds, COALESCE(SUM(main_tbl.stamp), 0) AS stamp,
                        COALESCE(SUM(main_tbl.bank_pay), 0) AS bank_pay, COALESCE(SUM(main_tbl.cash_pay), 0) AS cash_pay
                    FROM (
                        SELECT COUNT(tbl1.emp_id) AS emp_count, tbl1.loc_id, COALESCE(SUM(tbl1.basic), 0) AS basic, COALESCE(SUM(tbl1.house_rent), 0) AS house_rent,
                        COALESCE(SUM(tbl1.medical_alw), 0) AS medical_alw, COALESCE(SUM(tbl1.con_alw), 0) AS con_alw, COALESCE(SUM(tbl1.gross), 0) AS gross,
                        COALESCE(SUM(tbl2.holy_day), 0) AS holy_day, COALESCE(SUM(tbl1.tpf), 0) AS tpf,
                        COALESCE(SUM(tbl2.absent_day), 0) AS absent_day, COALESCE(SUM(tbl2.present_day),0) AS present_day, COALESCE(SUM(tbl2.day_of_month),0) AS day_of_month,
                        COALESCE(SUM(tbl1.ab_amt), 0) AS ab_amt, COALESCE(SUM(tbl1.total_payable_sal), 0) AS total_payable_sal, COALESCE(SUM(tbl1.adv_salary),0) AS adv_salary,
                        COALESCE(SUM(tbl1.loan),0) AS loan, COALESCE(SUM(tbl1.tds),0) AS tds, COALESCE(SUM(tbl1.stamp), 0) AS stamp,
                        COALESCE(SUM(tbl1.bank_pay), 0) AS bank_pay, COALESCE(SUM(tbl1.cash_pay), 0) AS cash_pay
                        FROM(
                            SELECT he.id AS emp_id, hp.user_work_location_id AS loc_id,
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
                            LEFT JOIN hr_payslip hp ON hp.employee_id = he.id
                            LEFT JOIN hr_payslip_line hpl ON hpl.slip_id = hp.id
                            LEFT JOIN hr_payroll_structure hps ON hps.id = hp.struct_id   
                            {7} JOIN (
                                    SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                    JOIN hr_employee_category etag on etag.id=ecr.category_id
                                    {6}
                                    GROUP BY emp_id
                                ) emp_tag ON emp_tag.emp_id = he.id                     
                            WHERE hps.code = 'BASE' AND DATE(hp.date_to) BETWEEN '{0}' AND '{1}' {2} {3} {4} {5}
                            GROUP BY he.id, hp.user_work_location_id, hp.cash_amount, hp.bank_amount
                            ORDER BY hp.user_work_location_id
                            ) tbl1
                            LEFT JOIN (
                                SELECT ast.employee_id, COUNT(astl.id) AS holy_day, COALESCE(ast.no_absence + ast.actual_late_count, 0) AS absent_day, ast.no_presence AS present_day, ast.no_of_days AS day_of_month
                                FROM attendance_sheet ast
                                LEFT JOIN attendance_sheet_line astl ON astl.att_sheet_id = ast.id
                                WHERE astl.status in ('ph', 'weekend')
                                AND ast.state='done' AND DATE(ast.date_to) BETWEEN '{0}' AND '{1}'
                                GROUP BY ast.employee_id, ast.no_absence, ast.no_presence, ast.no_of_days, ast.actual_late_count
                        ) tbl2 ON tbl2.employee_id = tbl1.emp_id
                        GROUP BY tbl1.loc_id
                        ORDER BY tbl1.loc_id
                    ) main_tbl
                    LEFT JOIN stock_location sl ON sl.id = main_tbl.loc_id
                    GROUP BY sl.name, main_tbl.emp_count
                    ORDER BY sl.name
                    """.format(start_date, end_date,
                                state_filter, work_loc_filter, 
                                include_non_zero_payable_filter, business_unit_filter,
                                tags_filter, tag_filter_join)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        data = {
            'model': "location.wise.employee.salary.sheet.report.wizard",
            'form': self.read()[0],
            'csr': data_res,
            'month': dict(self._fields['month'].selection).get(self.month),
            'year': year,
            'state_name': state_name,
            'work_loc_name': work_location_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
            
        }
        return data

    #not used/ bcoz wrong sql
    def x_location_wise_employee_salary_summary_report_sql(self, month, year, state, user_work_location_id, include_zero_less_payable):
        m = int(month)
        y = int(year)
        ndays = monthrange(y, m)[1]
        start_date = date(y, m, 1)
        end_date = date(y, m, ndays)

        work_loc_filter = ""
        state_filter = ""
        state_name = ""
        work_location_name = "All"
        include_non_zero_payable_filter = ""

        if state:
            state_filter = "AND hp.state = '%s'" % state
            state_name = dict(self._fields['state'].selection).get(self.state)

        if user_work_location_id:
            work_loc_filter = "AND he.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if not include_zero_less_payable:
            include_non_zero_payable_filter = "AND (hp.cash_amount > 0 OR hp.bank_amount > 0)"

        data_sql = """
                    SELECT sl.name AS loc_name, main_tbl.emp_count AS emp_count, COALESCE(SUM(main_tbl.basic), 0) AS basic, COALESCE(SUM(main_tbl.house_rent), 0) AS house_rent,
                        COALESCE(SUM(main_tbl.medical_alw), 0) AS medical_alw, COALESCE(SUM(main_tbl.con_alw), 0) AS con_alw, COALESCE(SUM(main_tbl.gross), 0) AS gross_salary,
                        COALESCE(SUM(main_tbl.holy_day), 0) AS holy_day, COALESCE(SUM(main_tbl.tpf), 0) AS pf,
                        COALESCE(SUM(main_tbl.absent_day), 0) AS absent_day, COALESCE(SUM(main_tbl.present_day),0) AS present_day, COALESCE(SUM(main_tbl.day_of_month),0) AS day_of_month,
                        COALESCE(SUM(main_tbl.ab_amt), 0) AS abs_amt, COALESCE(SUM(main_tbl.total_payable_sal), 0) AS payable_salary, COALESCE(SUM(main_tbl.adv_salary),0) AS advance_amount,
                        COALESCE(SUM(main_tbl.loan),0) AS loan_adj, COALESCE(SUM(main_tbl.tds),0) AS tds, COALESCE(SUM(main_tbl.stamp), 0) AS stamp,
                        COALESCE(SUM(main_tbl.bank_pay), 0) AS bank_pay, COALESCE(SUM(main_tbl.cash_pay), 0) AS cash_pay
                    FROM (
                        SELECT COUNT(tbl1.emp_id) AS emp_count, tbl1.loc_id, COALESCE(SUM(tbl1.basic), 0) AS basic, COALESCE(SUM(tbl1.house_rent), 0) AS house_rent,
                        COALESCE(SUM(tbl1.medical_alw), 0) AS medical_alw, COALESCE(SUM(tbl1.con_alw), 0) AS con_alw, COALESCE(SUM(tbl1.gross), 0) AS gross,
                        COALESCE(SUM(tbl2.holy_day), 0) AS holy_day, COALESCE(SUM(tbl1.tpf), 0) AS tpf,
                        COALESCE(SUM(tbl2.absent_day), 0) AS absent_day, COALESCE(SUM(tbl2.present_day),0) AS present_day, COALESCE(SUM(tbl2.day_of_month),0) AS day_of_month,
                        COALESCE(SUM(tbl1.ab_amt), 0) AS ab_amt, COALESCE(SUM(tbl1.total_payable_sal), 0) AS total_payable_sal, COALESCE(SUM(tbl1.adv_salary),0) AS adv_salary,
                        COALESCE(SUM(tbl1.loan),0) AS loan, COALESCE(SUM(tbl1.tds),0) AS tds, COALESCE(SUM(tbl1.stamp), 0) AS stamp,
                        COALESCE(SUM(tbl1.bank_pay), 0) AS bank_pay, COALESCE(SUM(tbl1.cash_pay), 0) AS cash_pay
                        FROM(
                            SELECT he.id AS emp_id, he.user_work_location_id AS loc_id,
                            hc.wage AS basic, hc.hra AS house_rent, hc.medical_allowance AS medical_alw, hc.travel_allowance AS con_alw,
                            hc.gross_salary AS gross,
                            SUM(CASE WHEN hpl.code = 'ABS' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS ab_amt,
                            SUM(CASE WHEN hpl.code = 'NET' THEN COALESCE(hpl.amount, 0) ELSE 0 END) AS total_payable_sal,
                            SUM(CASE WHEN hpl.code = 'SAR' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS adv_salary,
                            SUM(CASE WHEN hpl.code in ('LOANINS', 'LOANINT') THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS loan,
                            SUM(CASE WHEN hpl.code = 'PF' THEN COALESCE((-1) * hpl.amount, 0) ELSE 0 END) AS tpf,
                            hc.tds_deduction AS tds, hc.stamp_deduction AS stamp, hp.bank_amount AS bank_pay, hp.cash_amount AS cash_pay
                            FROM hr_employee he
                            LEFT JOIN hr_contract hc ON hc.employee_id = he.id
                            LEFT JOIN hr_payslip hp ON hp.employee_id = he.id
                            LEFT JOIN hr_payslip_line hpl ON hpl.slip_id = hp.id
                            WHERE hc.state = 'open' AND DATE(hp.date_to) BETWEEN '{0}' AND '{1}' {2} {3} {4}
                            GROUP BY he.id, he.user_work_location_id, hc.wage , hc.hra, hc.medical_allowance, hp.cash_amount, hp.bank_amount, hc.travel_allowance, hc.gross_salary, hc.tds_deduction, hc.stamp_deduction
                            ORDER BY he.user_work_location_id
                            ) tbl1
                            LEFT JOIN (
                                SELECT ast.employee_id, COUNT(astl.id) AS holy_day, COALESCE(ast.no_absence + ast.actual_late_count, 0) AS absent_day, ast.no_presence AS present_day, ast.no_of_days AS day_of_month
                                FROM attendance_sheet ast
                                LEFT JOIN attendance_sheet_line astl ON astl.att_sheet_id = ast.id
                                WHERE astl.status in ('ph', 'weekend')
                                AND ast.state='done' AND DATE(ast.date_to) BETWEEN '{0}' AND '{1}'
                                GROUP BY ast.employee_id, ast.no_absence, ast.no_presence, ast.no_of_days, ast.actual_late_count
                        ) tbl2 ON tbl2.employee_id = tbl1.emp_id
                        GROUP BY tbl1.loc_id
                        ORDER BY tbl1.loc_id
                    ) main_tbl
                    LEFT JOIN stock_location sl ON sl.id = main_tbl.loc_id
                    GROUP BY sl.name, main_tbl.emp_count
                    ORDER BY sl.name
                    """.format(start_date, end_date, state_filter, work_loc_filter, include_non_zero_payable_filter)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        data = {
            'model': "location.wise.employee.salary.sheet.report.wizard",
            'form': self.read()[0],
            'csr': data_res,
            'month': dict(self._fields['month'].selection).get(self.month),
            'year': year,
            'state_name': state_name,
            'work_loc_name': work_location_name,
        }
        return data