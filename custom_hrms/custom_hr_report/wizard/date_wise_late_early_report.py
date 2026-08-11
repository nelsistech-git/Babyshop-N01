from odoo import fields, models, api, _
import datetime
from calendar import monthrange
from datetime import datetime
from datetime import date
from odoo.exceptions import ValidationError
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


class DateWiseLateEarlyReportWizard(models.TransientModel):
    _name = "date.wise.late.early.report.wizard"
    _description = "Date wise Late-Early Report Wizard"

    file_data = fields.Binary('Date wise Late Early Report Wizard')
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

    category_ids = fields.Many2many('hr.employee.category', 'date_wise_late_early_employee_category_rel', 
                    'selected_id', 'category_id', string='Tags')
        
    sbu_unit_id = fields.Many2one('hr.sbu.unit', string='Office/Business Unit')

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
    def _set_domain_work_loc(self):
        if self.env.user.user_work_location_id:
            return [('is_work_loc', '=', True), ('state', '=', 'done'), ('id', '=', self.env.user.user_work_location_id.id)]
        else:
            return [('is_work_loc', '=', True), ('state', '=', 'done')]

    @api.model
    def _get_work_loc(self):
        if self.env.user.user_work_location_id:
            return self.env.user.user_work_location_id.id

    def date_wise_late_early_report_excel(self):
        from_date = self.from_date
        to_date = self.to_date
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.date_wise_late_early_report_sql(from_date, to_date, department_id, user_work_location_id)

        file_name = "Date wise Late-Early Report (%s - %s).xlsx" % (data['form']['from_date'], data['form']['to_date'])
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

        for line in data['csr']:
            for line2 in line:
                sheet = workbook.add_worksheet(line[line2][0]['location_name'])

                sheet.merge_range(0, 0, 0, 8, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 2, 8,
                                  "Date wise Late-Early Report (%s - %s)" % (
                                          data['form']['from_date'], data['form']['to_date']),
                                          format0)

                sheet.merge_range(3, 0, 3, 2, 'Work/Job Location: {0}'.format(line[line2][0]['location_name']), format1)
                sheet.merge_range(3, 3, 3, 4, 'Department Name: {0}'.format(data['dept_name']), format1)
                sheet.merge_range(3, 5, 3, 6, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
                sheet.merge_range(3, 7, 3, 8, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)


                sheet.write(4, 0, 'Employee Name', format1)
                sheet.write(4, 1, 'Employee ID No', format1)
                sheet.write(4, 2, 'Department', format1)
                sheet.write(4, 3, 'Designation', format1)
                sheet.write(4, 4, 'Actual Late Days', format2)
                sheet.write(4, 5, 'Deduction Absent', format2)
                sheet.write(4, 6, 'Real Absent Days', format2)
                sheet.write(4, 7, 'Total Absent Day', format2)
                sheet.write(4, 8, 'Early Out', format2)

                row = 5
                col = 0

                for line3 in line[line2]:
                    sheet.write(row, col, line3['employee_name'], format4)
                    sheet.write(row, col + 1, line3['emp_id_card'], format4)
                    sheet.write(row, col + 2, line3['department_name'], format4)
                    sheet.write(row, col + 3, line3['designation_name'], format4)
                    sheet.write(row, col + 4, line3['total_late'], format5)
                    sheet.write(row, col + 5, line3['deduct_abs'], format5)
                    sheet.write(row, col + 6, line3['total_ab'], format5)
                    sheet.write(row, col + 7, line3['total_ab_with_deduct'], format5)
                    sheet.write(row, col + 8, line3['early_out'], format5)

                    row = row + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Date wise Late-Early Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=date.wise.late.early.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def date_wise_late_early_report_pdf(self):
        from_date = self.from_date
        to_date = self.to_date
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.date_wise_late_early_report_sql(from_date, to_date, department_id, user_work_location_id)

        return self.env.ref(
            'custom_hr_report.date_wise_late_early_report_tmpl').with_context(landscape=True).report_action(self, data=data)

    def date_wise_late_early_report_sql(self, from_date, to_date, department_id, user_work_location_id):
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

        # data_sql = """
        #             SELECT main_tbl.emp_id_card, main_tbl.employee_name, hd.name AS dept_name, hj.name AS job_name, COALESCE(main_tbl.total_late, 0) AS total_late,
        #             COALESCE(main_tbl.deduct_abs, 0) AS deduct_abs, COALESCE(main_tbl.total_ab, 0) AS total_ab, COALESCE(main_tbl.total_ab_with_deduct, 0) AS total_ab_with_deduct, COALESCE(main_tbl.early_out, 0) AS early_out
        #             FROM(
        #                 SELECT hr.name AS employee_name, hr.job_id AS job_id, hr.id_card_no AS emp_id_card, ast.department_id AS department_id,
        #                 COALESCE(ast.no_late, 0) AS total_late, COALESCE(ast.actual_late_count, 0) AS deduct_abs, COALESCE(ast.no_absence, 0) AS total_ab, COALESCE(ast.actual_late_count+ast.no_absence, 0) AS total_ab_with_deduct, COALESCE(ast.actual_diff_count, 0) AS early_out
        #                 FROM attendance_sheet ast
        #                 JOIN attendance_sheet_line asl ON asl.att_sheet_id = ast.id
        #                 JOIN hr_employee hr ON hr.id = ast.employee_id
        #                 WHERE DATE(ast.date_from) Between '{0}' AND '{1}'
        #                 {2} {3}
        #                 GROUP BY hr.name, hr.job_id, hr.id_card_no, ast.department_id, ast.no_late,ast.actual_late_count, ast.no_absence, ast.actual_diff_count
        #                 ORDER BY hr.name
        #             ) main_tbl
        #             LEFT JOIN hr_department hd on hd.id = main_tbl.department_id
        #             LEFT JOIN hr_job hj ON hj.id = main_tbl.job_id
        #             GROUP BY main_tbl.emp_id_card, main_tbl.employee_name, hd.name, hj.name, main_tbl.total_late,main_tbl.deduct_abs, main_tbl.total_ab,main_tbl.total_ab_with_deduct, main_tbl.early_out
        #             ORDER BY main_tbl.emp_id_card, main_tbl.employee_name
        #             """.format(start_date, end_date, dept_filter, work_loc_filter)

        data_sql = """
                    SELECT main_tbl.emp_id, main_tbl.employee_name, main_tbl.emp_id_card, hd.name->>'en_US' AS department_name, hj.name->>'en_US' AS designation_name, main_tbl.late_days, sl.name AS location_name, 
                    COALESCE(main_tbl.work_loc_id, 100000) AS user_work_location_id,
                    COALESCE(SUM(main_tbl.act_late_days), 0)::INT AS total_late,
                    COALESCE(SUM(main_tbl.absent_day), 0)::INT AS total_ab,
                    COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0)), 0)::INT AS deduct_abs,
                    COALESCE(COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0))::INT, 0) + main_tbl.absent_day, 0) AS total_ab_with_deduct,
                    COALESCE(SUM(main_tbl.early_out/NULLIF(hap.salary_ded_count_early_out, 0)), 0)::INT AS early_out
                    FROM (
                        SELECT he.id AS emp_id, he.name AS employee_name, he.id_card_no AS emp_id_card, he.department_id AS dept_id, he.job_id AS des_id,
                        he.user_work_location_id AS work_loc_id,hc.att_policy_id,
                        array_to_string(array_agg(CASE WHEN easl.late_in > 0 THEN EXTRACT(DAY FROM easl.date)  ELSE NULL END), ', ')  AS late_days,
                        COALESCE(SUM(CASE WHEN easl.late_in > 0 THEN 1 ELSE 0 END), 0) AS act_late_days,
                        COALESCE(SUM(CASE WHEN easl.status = 'ab' THEN 1 ELSE 0 END), 0) AS absent_day,
                        COALESCE(SUM(CASE WHEN easl.diff_time > 0 AND (easl.status IS NULL OR easl.status IN ('weekend', 'ph', 'leave')) THEN 1 ELSE 0 END), 0) AS early_out
                        FROM hr_employee he
                        JOIN hr_contract hc ON hc.employee_id = he.id
                        JOIN employee_attendance_sheet_line easl ON easl.employee_id = he.id
                        {6} JOIN (
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {4}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = he.id
                        WHERE hc.state = 'open' AND he.active = true
                        AND DATE(easl.date) BETWEEN '{0}' AND '{1}'
                        {2} {3} {5}
                        GROUP BY he.id, hc.att_policy_id
                        ORDER BY he.name
                    ) main_tbl
                    LEFT JOIN hr_department hd on hd.id = main_tbl.dept_id
                    LEFT JOIN hr_job hj ON hj.id = main_tbl.des_id
                    LEFT JOIN stock_location sl ON sl.id = main_tbl.work_loc_id
                    LEFT JOIN hr_attendance_policy hap ON hap.id = main_tbl.att_policy_id
                    GROUP BY main_tbl.emp_id,main_tbl.employee_name,main_tbl.emp_id_card,hd.name, hj.name, main_tbl.late_days,main_tbl.work_loc_id,
                    main_tbl.act_late_days,main_tbl.absent_day, sl.name
                    ORDER BY {7}
                    """.format(from_date, to_date,
                                dept_filter, work_loc_filter,
                                tags_filter, business_unit_filter, 
                                tag_filter_join, order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()
        # data_list = []
        #
        # for d in data_res:
        #     vals = {
        #         'employee_name': d['employee_name'],
        #         'designation_name': d['job_name'],
        #         'emp_id_card': d['emp_id_card'],
        #         'department_name': d['dept_name'],
        #         'total_late': d['total_late'],
        #         'deduct_abs': d['deduct_abs'],
        #         'total_ab': d['total_ab'],
        #         'total_ab_with_deduct': d['total_ab_with_deduct'],
        #         'early_out': d['early_out']
        #
        #     }
        #     data_list.append(vals)

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
            'model': "date.wise.late.early.report.wizard",
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
