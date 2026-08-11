from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import datetime
from datetime import datetime
from itertools import groupby
import xlsxwriter

import base64
from io import BytesIO


def get_years():
    year_list = []
    crn_year = datetime.now().year
    for i in range(2022, crn_year + 5):
        year_list.append((str(i), str(i)))
    return year_list


class AreaDeductAdjustSalaryReportWizard(models.TransientModel):
    _name = "area.deduct.adjust.salary.report.wizard"
    _description = "Area Deduct Adjust Salary Report Wizard"

    file_data = fields.Binary('Area Deduct Adjust Salary Report')
    # year = fields.Selection(get_years(), string='Year', dafault='10', required=True)
    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', default=lambda self: self._get_work_loc(), domain=lambda self: self._set_domain_work_loc())
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    # month = fields.Selection([
    #     ('01', 'January'),
    #     ('02', 'February'),
    #     ('03', 'March'),
    #     ('04', 'April'),
    #     ('05', 'May'),
    #     ('06', 'June'),
    #     ('07', 'July'),
    #     ('08', 'August'),
    #     ('09', 'September'),
    #     ('10', 'October'),
    #     ('11', 'November'),
    #     ('12', 'December'),
    # ], string='Month', required=True)

    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')

    category_ids = fields.Many2many('hr.employee.category', 'area_deduct_adjust_salary_employee_category_rel', 
                'selected_id', 'category_id', string='Tags')

    sbu_unit_id = fields.Many2one('hr.sbu.unit', string='Office/Business Unit')

    @api.model
    def _set_domain_work_loc(self):
        if self.env.user.user_work_location_id:
            return [('is_work_loc', '=', True), ('state', '=', 'done'), ('id', '=', self.env.user.user_work_location_id.id)]
        else:
            return [('is_work_loc', '=', True), ('state', '=', 'done')]

    @api.constrains('from_date', 'to_date')
    def date_constrains(self):
        from_date_year = datetime.strptime(str(self.from_date), '%Y-%m-%d').strftime('%Y')
        to_date_year = datetime.strptime(str(self.to_date), '%Y-%m-%d').strftime('%Y')
        from_date_month = datetime.strptime(str(self.from_date), '%Y-%m-%d').strftime('%m')
        to_date_month = datetime.strptime(str(self.to_date), '%Y-%m-%d').strftime('%m')
        if self.to_date < self.from_date:
            raise ValidationError(_('From date cannot be less than the to date.'))

        if from_date_year != to_date_year:
            raise ValidationError(_('Validity from date and to date must be of the year.'))

        if from_date_year == to_date_year:
            if from_date_month != to_date_month:
                raise ValidationError(_('Validity from date and to date must be of same the month.'))

    @api.model
    def _get_work_loc(self):
        if self.env.user.user_work_location_id:
            return self.env.user.user_work_location_id.id

    def area_deduct_adjust_salary_report_pdf(self):
        from_date = self.from_date
        to_date = self.to_date
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.area_deduct_adjust_salary_report_sql(from_date, to_date, department_id, user_work_location_id)
        return self.env.ref(
            'custom_hr_report.area_deduct_adjust_salary_report_tmpl').with_context(landscape=True).report_action(self,
                                                                                                                   data=data)

    def area_deduct_adjust_salary_report_excel(self):
        from_date = self.from_date
        to_date = self.to_date
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.area_deduct_adjust_salary_report_sql(from_date, to_date, department_id, user_work_location_id)

        file_name = "Area Deduction Adjustment Salary Report (%s - %s).xlsx" % (data['form']['from_date'], data['form']['to_date'])
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

        for line in data['csr']:
            for line2 in line:
                sheet = workbook.add_worksheet(line[line2][0]['location_name'])

                sheet.merge_range(0, 0, 0, 9, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 2, 9, "Area Deduction Adjustment Salary Report (%s - %s)" % (
                                  data['form']['from_date'], data['form']['to_date']),
                                  format0)
                # sheet.merge_range(3, 0, 3, 9, "For the month of %s - %s" % (data['month'], data['year']), format0)

                sheet.merge_range(4, 0, 4, 5, 'Work/Job Location: {0}'.format(line[line2][0]['location_name']), format1)
                sheet.merge_range(5, 0, 5, 5, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)

                sheet.merge_range(4, 6, 4, 9, 'Department Name: {0}'.format(data['dept_name']), format3)
                sheet.merge_range(5, 6, 5, 9, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format3)

                sheet.write(6, 0, 'Employee ID', format2)
                sheet.write(6, 1, 'Employee Name', format1)
                sheet.write(6, 2, 'Joining Date', format2)
                sheet.write(6, 3, 'Work Location', format1)
                sheet.write(6, 4, 'Department', format1)
                sheet.write(6, 5, 'Designation', format1)
                sheet.write(6, 6, 'Absent Day', format2)
                sheet.write(6, 7, 'Gross Salary', format3)
                sheet.write(6, 8, 'Deducted Amount', format3)
                sheet.write(6, 9, 'Remarks', format2)

                row = 7
                col = 0

                for line3 in line[line2]:
                    sheet.write(row, col + 0, line3['emp_id_card'], format5)
                    sheet.write(row, col + 1, line3['employee_name'], format4)
                    joining_date = datetime.strptime(str(line3['joining_date']), '%Y-%m-%d').strftime('%d-%b-%Y') if line3['joining_date'] else None
                    sheet.write(row, col + 2, joining_date, format5)
                    sheet.write(row, col + 3, line3['location_name'], format4)
                    sheet.write(row, col + 4, line3['dept_name'], format4)
                    sheet.write(row, col + 5, line3['job_name'], format4)
                    sheet.write(row, col + 6, line3['total_ab_with_deduct'], format5)
                    sheet.write(row, col + 7, round(line3['gross_salary'], 2), format6)
                    sheet.write(row, col + 8, round(line3['total_ab_with_deduct'] * line3['per_day_salary'], 2), format6)
                    sheet.write(row, col + 9, None, format5)

                    row = row + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Area Deduction Adjustment Salary Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=area.deduct.adjust.salary.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    # need to edit this sql (billal-05-11-2023)
    def area_deduct_adjust_salary_report_sql(self, from_date, to_date, department_id, user_work_location_id):
        # m = int(month)
        # y = int(year)
        # ndays = monthrange(y, m)[1]
        # start_date = date(y, m, 1)
        # end_date = date(y, m, ndays)

        dept_filter = ""
        work_loc_filter = ""
        dept_name = "All"
        work_location_name = "All"
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"
        order_by = "main_tbl.employee_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "main_tbl.emp_id_card"
        print(order_by)

        if department_id:
            dept_filter = "AND he.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            work_loc_filter = "AND he.user_work_location_id = %s" % user_work_location_id.id
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
                    SELECT main_tbl.emp_id,main_tbl.emp_id_card,main_tbl.employee_name,main_tbl.joining_date, sl.name AS location_name, hd.name->>'en_US' AS dept_name,
                   hj.name->>'en_US' AS job_name,
                    COALESCE(main_tbl.work_loc_id, 100000) AS user_work_location_id,
                    COALESCE(COALESCE(SUM(main_tbl.act_late_days/hap.salary_ded_count_late)::INT, 0) + main_tbl.absent_day, 0) AS total_ab_with_deduct,
                    main_tbl.gross_salary,
                    --COALESCE(SUM(CASE WHEN hap.work_day_without_week_ph = True THEN main_tbl.gross_salary/main_tbl.no_of_days ELSE 
                    --CASE WHEN hap.work_day_without_week_ph = False THEN main_tbl.gross_salary/main_tbl.no_of_days_w ELSE 0 END END), 0) AS per_day_salary
                    
                    COALESCE(SUM(main_tbl.gross_salary/main_tbl.no_of_days), 0) AS per_day_salary
                    
                    FROM (
                        SELECT he.id AS emp_id, he.name AS employee_name, he.id_card_no AS emp_id_card, he.initial_employment_date AS joining_date,he.department_id AS dept_id, he.job_id AS des_id,
                        he.user_work_location_id AS work_loc_id, hc.att_policy_id, hc.gross_salary as gross_salary,
                        array_to_string(array_agg(CASE WHEN easl.late_in > 0 THEN EXTRACT(DAY FROM easl.date)  ELSE NULL END), ', ')  AS late_days,
                        COALESCE(SUM(CASE WHEN easl.late_in > 0 THEN 1 ELSE 0 END), 0) AS act_late_days,
                        COALESCE(SUM(CASE WHEN easl.status = 'ab' THEN 1 ELSE 0 END), 0) AS absent_day,
                        
                        --COALESCE(SUM(CASE WHEN easl.status in ('ab', 'leave') OR easl.status IS NULL THEN 1 ELSE 0 END), 0) AS no_of_days,                        
                        COALESCE(SUM(CASE WHEN (easl.status in ('ab', 'leave')) OR easl.status IS NULL OR (easl.status ='weekend' AND hapm.work_day_without_week_ph = False) OR (easl.status ='ph' AND hapm.work_day_without_ph = False) THEN 1 ELSE 0 END), 0) AS no_of_days,
                        COALESCE(SUM(CASE WHEN easl.status in ('ab', 'leave', 'weekend', 'ph') OR easl.status IS NULL THEN 1 ELSE 0 END), 0) AS no_of_days_w
                        
                        FROM hr_employee he
                        JOIN hr_contract hc ON hc.employee_id = he.id
                        JOIN employee_attendance_sheet_line easl ON easl.employee_id = he.id
                        JOIN hr_attendance_policy hapm ON hapm.id = hc.att_policy_id
                        {6} JOIN (
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {5}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = he.id
                        WHERE hc.state = 'open' AND he.active = true
                        AND DATE(easl.date) BETWEEN '{0}' AND '{1}' {2} {3} {4}
                        GROUP BY he.id, hc.att_policy_id, hc.gross_salary
                        ORDER BY he.name
                    ) main_tbl
                    LEFT JOIN hr_department hd on hd.id = main_tbl.dept_id
                    LEFT JOIN hr_job hj ON hj.id = main_tbl.des_id
                    LEFT JOIN stock_location sl ON sl.id = main_tbl.work_loc_id
                    LEFT JOIN hr_attendance_policy hap ON hap.id = main_tbl.att_policy_id
                    GROUP BY main_tbl.emp_id,main_tbl.employee_name,main_tbl.emp_id_card,hd.name, hj.name, main_tbl.late_days,main_tbl.work_loc_id,
                    main_tbl.act_late_days,main_tbl.absent_day, sl.name, main_tbl.joining_date, main_tbl.gross_salary
                    ORDER BY {7}
                    """.format(from_date, to_date,
                                dept_filter, work_loc_filter,
                                business_unit_filter, tags_filter,
                                tag_filter_join, order_by)
        self.env.cr.execute(data_sql)

        data_res = self.env.cr.dictfetchall()

        # define a fuction for key
        def key_func(k):
            return k['user_work_location_id']

        data_res = sorted(data_res, key=key_func)

        final_data_list = []

        for key, value in groupby(data_res, key_func):
            vals = {
                key: list(value)
            }
            final_data_list.append(vals)

        data = {
            'model': "area.deduct.adjust.salary.report.wizard",
            'form': self.read()[0],
            'csr': final_data_list,
            # 'month': dict(self._fields['month'].selection).get(self.month),
            # 'year': year,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data