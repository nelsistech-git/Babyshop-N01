from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from calendar import monthrange
import datetime
from datetime import datetime, date, timedelta
import copy
import xlsxwriter
import base64
from io import BytesIO


class DailyAttendanceStatisticReportWizard(models.TransientModel):
    _name = "daily.attendance.statistic.report.wizard"
    _description = "Daily Attendance Statistic Report Wizard"

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
                    list_format = '%s' % i, str(i)
                    year_list.append(list_format)
        else:
            if company.display_year:
                start_year = datetime.today().year
                display_years = company.display_year
                for i in range(start_year, start_year + display_years, 1):
                    list_format = '%s' % i, str(i)
                    year_list.append(list_format)
            else:
                list_format = '%s' % datetime.today().year, datetime.today().year
                year_list.append(list_format)
        return year_list

    def _default_year(self):
        year = str(datetime.today().year)
        return year or ''

    file_data = fields.Binary('Daily Attendance Statistic Report Wizard')
    year = fields.Selection(get_years, string='Year', default=_default_year)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    department_ids = fields.Many2many('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')
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
    ], string='Month')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    is_deducted = fields.Boolean(string='Apply Attendance Policy', default=True)
    report_type = fields.Selection([
        ('all', 'All'),
        ('current_emp', 'Current Employee'),
        ('resign_emp', 'Resign Employee'),
    ], string='Report Type', default='all')

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

    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       default=lambda self: self._get_work_loc(),
                                       domain=lambda self: self._set_domain_work_loc())


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

    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('Start date cannot be greater than the end date.'))

    @api.onchange('user_work_location_id', 'department_ids')
    def _onchange_employees(self):
        domain = []

        if self.user_work_location_id:
            domain += [('user_work_location_id', '=', self.user_work_location_id.id)]

        if self.department_ids:
            domain += [('department_id', 'in', self.department_ids.ids)]

        return {'domain': {
            'employee_id': domain,
        }}

    category_ids = fields.Many2many('hr.employee.category', 'daily_attendance_statistic_employee_category_rel', 'selected_id', 'category_id', string='Tags')
    
    sbu_unit_id = fields.Many2one('hr.sbu.unit', string='Office/Business Unit')


    def daily_attendance_statistic_report_html(self):
        year = self.year
        month = self.month
        user_work_location_id = self.user_work_location_id
        department_ids = self.department_ids
        employee_id = self.employee_id
        report_type = self.report_type

        # get data from sql
        if self._context.get('is_sheet'):
            data = self.daily_attendance_statistic_report_sql_sheet(year, month, user_work_location_id, department_ids,
                                                                    employee_id, report_type)
        else:
            data = {
                'ftr_id': self.id
            }

        return self.env.ref(
            'custom_hr_attendance_sheet.daily_attendance_statistic_report_view_tmpl').with_context(
            landscape=True).report_action(self, data=data)

    def daily_attendance_statistic_report_pdf(self):
        year = self.year
        month = self.month
        user_work_location_id = self.user_work_location_id
        department_ids = self.department_ids
        employee_id = self.employee_id
        report_type = self.report_type

        data = {
            'ftr_id': self.id
        }

        return self.env.ref(
            'custom_hr_attendance_sheet.daily_attendance_statistic_report_tmpl').with_context(
            landscape=True).report_action(self, data=data)

    def daily_attendance_statistic_report_excel(self):
        year = self.year
        month = self.month
        user_work_location_id = self.user_work_location_id
        department_ids = self.department_ids
        employee_id = self.employee_id
        report_type = self.report_type

        # get data from sql
        if self._context.get('is_sheet'):
            data = self.daily_attendance_statistic_report_sql_sheet(year, month, user_work_location_id, department_ids,
                                                                    employee_id, report_type)
        else:
            data = self.daily_attendance_statistic_report_sql_att()

        file_name = "Daily Attendance Statistic Report ({0} - {1}).xlsx".format(data['month'], data['year'])
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

        sheet = workbook.add_worksheet('Daily Attendance Statistic Report')

        day_list = data['day_list']
        week_days = data['week_days']

        # heading start
        main_head_col = 12 + len(day_list)
        sheet.merge_range(0, 0, 0, main_head_col, "{0}".format(data['form']['company_id'][1]), format0)
        sheet.merge_range(1, 0, 2, main_head_col,
                          "Daily Attendance Statistic Report ({0} - {1})".format(data['month'], data['year']), format0)

        # sheet.merge_range(3, 0, 3, int(main_head_col / 2), 'Work/Job Location: {0}'.format(data['work_location_name']),
        #                   format1)
        # sheet.merge_range(3, int(main_head_col / 2) + 1, 3, main_head_col,
        #                   'Department Name: {0}'.format(data['dept_name']), format3)
        sheet.merge_range(
            3, 0, 3, int(main_head_col / 4),
            'Work/Job Location: {0}'.format(data['work_location_name']),
            format1
        )
        sheet.merge_range(
            3, int(main_head_col / 4) + 1, 3, int(main_head_col / 2),
            'Department Name: {0}'.format(data['dept_name']),
            format1
        )
        sheet.merge_range(
            3, int(main_head_col / 2) + 1, 3, int(3 * main_head_col / 4),
            'Office/Business Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Business Unit: All",
            format1
        )
        sheet.merge_range(
            3, int(3 * main_head_col / 4) + 1, 3, main_head_col -1,
            'Tags: {0}'.format(', '.join(self.category_ids.mapped('display_name'))) if self.category_ids else "Tags: No Tags Selected",
            format1
        )

        # heading end

        sheet.merge_range(4, 0, 5, 0, 'Sl. No.', format2)
        sheet.merge_range(4, 1, 5, 1, 'Employee ID', format1)
        sheet.merge_range(4, 2, 5, 2, 'Employee Name', format2)
        sheet.merge_range(4, 3, 5, 3, 'Device ID', format2)
        sheet.merge_range(4, 4, 5, 4, 'Work/Job Location', format1)

        head_col = 5

        for i in range(len(day_list)):
            sheet.write(4, head_col, day_list[i], format2)

            head_col = head_col + 1

        sheet.merge_range(4, head_col, 5, head_col, 'Working Days', format2)
        sheet.merge_range(4, head_col + 1, 5, head_col + 1, 'Present Days', format2)
        sheet.merge_range(4, head_col + 2, 5, head_col + 2, 'Absent Days', format2)
        sheet.merge_range(4, head_col + 3, 5, head_col + 3, 'Late Days', format2)
        sheet.merge_range(4, head_col + 4, 5, head_col + 4, 'Early Days', format2)
        sheet.merge_range(4, head_col + 5, 5, head_col + 5, 'Unpaid Leave', format2)
        sheet.merge_range(4, head_col + 6, 5, head_col + 6, 'Leave Days', format2)
        sheet.merge_range(4, head_col + 7, 5, head_col + 7, 'OT Days (W/PH)', format2)

        head_col2 = 5

        for j in range(len(week_days)):
            sheet.write(5, head_col2, week_days[j], format2)

            head_col2 = head_col2 + 1

        # excel body
        row = 6
        col = 0
        att_col = 5

        sl_no = 1

        for line in data['csr']:
            if not (line['work_days'] == 0 and line['present_days'] == 0 and line['absent_days'] == 0 and line[
                'late_days'] == 0 and line['early_out'] == 0 and line['leave_days'] == 0):
                new_col = 0
                sheet.write(row, col, sl_no, format5)
                new_col += 1
                sheet.write(row, col + new_col, line['old_emp_id'], format4)
                new_col += 1
                sheet.write(row, col + new_col, line['emp_name'], format5)
                new_col += 1
                sheet.write(row, col + new_col, line['device_id'], format5)
                new_col += 1
                sheet.write(row, col + new_col, line['loc_name'], format4)
                

                att_dict = line['att_day_list'][0]

                for line2 in att_dict:
                    sheet.write(row, att_col, att_dict[str(line2)], format5)

                    att_col = att_col + 1

                new_col = 0
                sheet.write(row, att_col, line['work_days'], format5)
                new_col += 1
                sheet.write(row, att_col + new_col, line['present_days'], format5)
                new_col += 1
                sheet.write(row, att_col + new_col, line['absent_days'], format5)
                new_col += 1
                sheet.write(row, att_col + new_col, line['late_days'], format5)
                new_col += 1
                sheet.write(row, att_col + new_col, line['early_out'], format5)
                new_col += 1
                sheet.write(row, att_col + new_col, line['unpaid_leave_days'], format5)
                new_col += 1
                sheet.write(row, att_col + new_col, line['leave_days'], format5)
                new_col += 1
                sheet.write(row, att_col + new_col, line['no_of_days_wph_ot'], format5)

                row = row + 1
                sl_no = sl_no + 1
                att_col = 5

        if data['leave_type_names']:
            sheet.merge_range(row + 1, 0, row + 1, main_head_col,
                              'Present="P", Absent="A", Overtime="OT", Weekend="W", Public Holiday="PH", {0}, Late & Early Out="LE", Late="L", Early Out="E", One Time Punch="O", Late & One Time Punch="LO"'.format(
                                  data['leave_type_names']), format1)
        else:
            sheet.merge_range(row + 1, 0, row + 1, main_head_col,
                              'Present="P", Absent="A", Overtime="OT", Weekend="W", Public Holiday="PH", Late & Early Out="LE", Late="L", Early Out="E", One Time Punch="O", Late & One Time Punch="LO"',
                              format1)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Daily Attendance Statistic Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=daily.attendance.statistic.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    # using now
    def daily_attendance_statistic_report_sql_att(self):
        start_date = self.start_date
        end_date = self.end_date
        delta = (end_date - start_date).days + 1

        year = self.year
        month = self.month
        user_work_location_id = self.user_work_location_id
        department_ids = self.department_ids
        employee_id = self.employee_id
        report_type = self.report_type

        if delta > 31:
            raise ValidationError('Unable to process due to date range is more than 31 days.')

        date_list = [(start_date + timedelta(days=i)) for i in range(delta)]

        day_list = [i.day for i in date_list]

        week_days = []

        for rec in date_list:
            if rec.weekday() == 0:
                week_days.append('Mon')
            elif rec.weekday() == 1:
                week_days.append('Tue')
            elif rec.weekday() == 2:
                week_days.append('Wed')
            elif rec.weekday() == 3:
                week_days.append('Thu')
            elif rec.weekday() == 4:
                week_days.append('Fri')
            elif rec.weekday() == 5:
                week_days.append('Sat')
            else:
                week_days.append('Sun')

        att_day_list = [{str(rec).replace('-', ''): '' for rec in date_list}]

        work_loc_filter = ""
        work_loc_filter2 = ""
        dept_filter = ""
        dept_filter2 = ""
        emp_filter = ""
        emp_filter2 = ""
        deductFilter = "False"
        work_location_name = "All"
        dept_name = "All"
        report_type_filter = ""
        tags_filter = ""
        business_unit_filter = ""
        tag_filter_join = "LEFT"
        order_by = "main_tbl.emp_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "main_tbl.old_emp_id"
        print(order_by)



        domain = []

        if user_work_location_id:
            domain += [('user_work_location_id', '=', user_work_location_id.id)]
            work_loc_filter = "AND hre.user_work_location_id = %s" % user_work_location_id.id
            work_loc_filter2 = "AND hl.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if len(department_ids) > 1:
            dept_filter = "AND hre.department_id in {0}".format(tuple(department_ids.ids))
            dept_filter2 = "AND hl.department_id in {0}".format(tuple(department_ids.ids))
            dept_name = ", ".join([d.name for d in department_ids])
        elif len(department_ids) == 1:
            dept_filter = "AND hre.department_id = %s" % department_ids.id
            dept_filter2 = "AND hl.department_id = %s" % department_ids.id
            dept_name = department_ids.name

        if employee_id:
            emp_filter = "AND hre.id = %s" % employee_id.id
            emp_filter2 = "AND hl.employee_id = %s" % employee_id.id

        if self.is_deducted:
            deductFilter = "True"

        if self.report_type == 'current_emp':
            report_type_filter = "AND hre.resigned = False"
        elif self.report_type == 'resign_emp':
            report_type_filter = "AND hre.resigned = True"     
            
        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])  
                
        if self.sbu_unit_id:
            business_unit_filter = "AND hre.sbu_unit_id = {0}".format(self.sbu_unit_id.id)
        

        data_sql = """
                    SELECT COALESCE(main_tbl.work_loc_id, 100000) AS user_work_location_id, sl.name AS loc_name,
                    main_tbl.emp_id, main_tbl.old_emp_id, main_tbl.emp_name, main_tbl.device_id,
                    
                    --COALESCE(SUM(CASE WHEN hap.work_day_without_week_ph = True THEN main_tbl.no_of_days ELSE 
                    --CASE WHEN hap.work_day_without_week_ph = False THEN main_tbl.no_of_days_w ELSE 0 END END)::INT, 0) AS no_of_days,
                    
                    COALESCE(SUM(CASE WHEN main_tbl.is_deduct = False THEN main_tbl.no_of_days_w ELSE 
                    CASE WHEN main_tbl.is_deduct = True THEN main_tbl.no_of_days ELSE 0 END END)::INT, 0) AS no_of_days,
                    
                    -- COALESCE(SUM(main_tbl.no_of_days)::INT, 0) AS no_of_days,
                    
                    --COALESCE(SUM(CASE WHEN hap.work_day_without_week_ph = True THEN main_tbl.no_of_days_wph_ot ELSE 0 END)::INT, 0) AS no_of_days_wph_ot,
                    COALESCE(SUM(main_tbl.no_of_days_wph_ot)::INT, 0) AS no_of_days_wph_ot,
                    
                    --COALESCE((CASE WHEN main_tbl.is_deduct = False THEN SUM(main_tbl.present_day ) ELSE
                    --CASE WHEN main_tbl.is_deduct = True THEN (SUM(CASE WHEN hap.work_day_without_week_ph = True THEN main_tbl.no_of_days ELSE 
                    --CASE WHEN hap.work_day_without_week_ph = False THEN main_tbl.no_of_days_w ELSE 0 END END) - (COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0))::INT, 0) + main_tbl.absent_day)) ELSE 0 END END)::INT, 0) AS no_presence,
                    
                    --(COALESCE(CASE WHEN main_tbl.is_deduct = False THEN SUM(main_tbl.present_day) ELSE
                    --CASE WHEN main_tbl.is_deduct = True THEN SUM(main_tbl.no_of_days) ELSE 0 END END) - COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0))::INT, 0) + main_tbl.absent_day)  AS no_presence,
                    
                    CASE WHEN main_tbl.is_deduct = False THEN COALESCE(SUM(main_tbl.present_day),0) ELSE
                        CASE WHEN main_tbl.is_deduct = True THEN (COALESCE(SUM(main_tbl.present_day)::INT,0) - COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0))::INT, 0) - COALESCE(SUM(main_tbl.early_out/NULLIF(hap.salary_ded_count_early_out, 0))::INT, 0)) ELSE 0 END END  AS no_presence,
                    
                    COALESCE((CASE WHEN main_tbl.is_deduct = False THEN SUM(main_tbl.absent_day) ELSE
                                CASE WHEN main_tbl.is_deduct = True THEN COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0))::INT, 0) + main_tbl.absent_day ELSE 0 END END)::INT, 0) AS no_absence,
                    COALESCE((CASE WHEN main_tbl.is_deduct = False THEN SUM(main_tbl.act_late_days) ELSE
                                CASE WHEN main_tbl.is_deduct = True THEN COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0))::INT, 0) ELSE 0 END END)::INT, 0) AS actual_late_count,
                    COALESCE(SUM(CASE WHEN main_tbl.is_deduct = False THEN main_tbl.early_out ELSE
                                 CASE WHEN main_tbl.is_deduct = True THEN main_tbl.early_out/NULLIF(hap.salary_ded_count_early_out, 0) ELSE 0 END END), 0)::INT AS actual_diff_count,
                    COALESCE(SUM(main_tbl.act_late_days), 0)::INT AS late_days,
                    COALESCE(SUM(main_tbl.early_out), 0)::INT AS early_days,
                    (SELECT COUNT(hld.id) AS unpaid_leave_days
                    FROM hr_leave hl
                    JOIN hr_leave_details hld ON hld.leave_id = hl.id
                    JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                    WHERE hl.state='validate' AND hlt.type_code = 'LWP' AND DATE(hld.leave_date) BETWEEN '{0}' AND '{1}' AND hl.employee_id = main_tbl.emp_id),
                    (SELECT COUNT(hld.id) AS leave_days
                    FROM hr_leave hl
                    JOIN hr_leave_details hld ON hld.leave_id = hl.id
                    JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                    WHERE hl.state='validate' AND hlt.type_code != 'LWP' AND DATE(hld.leave_date) BETWEEN '{0}' AND '{1}' AND hl.employee_id = main_tbl.emp_id),
                    COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0)), 0)::INT AS deduct_abs
                    FROM (
                        SELECT hre.id AS emp_id, hre.name AS emp_name, hre.id_card_no AS old_emp_id, hre.device_user_id AS device_id, hre.user_work_location_id AS work_loc_id, hc.att_policy_id, {5} AS is_deduct,
                        COALESCE(SUM(CASE WHEN easl.late_in > 0 THEN 1 ELSE 0 END), 0) AS act_late_days,
                        COALESCE(SUM(CASE WHEN easl.status = 'ab' THEN 1 ELSE 0 END), 0) AS absent_day,
                        COALESCE(SUM(CASE WHEN easl.pl_sign_in > 0 AND easl.status IS NULL THEN 1 ELSE 0 END), 0) AS present_day,
                        COALESCE(SUM(CASE WHEN easl.diff_time > 0 AND (easl.status IS NULL OR easl.status IN ('weekend', 'ph', 'leave')) THEN 1 ELSE 0 END), 0) AS early_out,
                        
                        COALESCE(SUM(CASE WHEN easl.status in ('ab', 'leave', 'weekend', 'ph') OR easl.status IS NULL THEN 1 ELSE 0 END), 0) AS no_of_days_w,
                        COALESCE(SUM(CASE WHEN (easl.status in ('ab', 'leave')) OR easl.status IS NULL OR (easl.status ='weekend' AND hapm.work_day_without_week_ph = False) OR (easl.status ='ph' AND hapm.work_day_without_ph = False) THEN 1 ELSE 0 END), 0) AS no_of_days,
                        
                        COALESCE(SUM(CASE WHEN (easl.status ='weekend' AND easl.worked_hours > 0 AND easl.ovt_flag ='1' AND hapm.work_day_without_week_ph = True) OR (easl.status = 'ph' AND easl.worked_hours > 0 AND easl.ovt_flag ='1' AND hapm.work_day_without_ph = True) THEN 1 ELSE 0 END), 0) AS no_of_days_wph_ot
                        
                        FROM hr_employee hre
                        JOIN hr_contract hc ON hc.employee_id = hre.id
                        JOIN employee_attendance_sheet_line easl ON easl.employee_id = hre.id
                        JOIN hr_attendance_policy hapm ON hapm.id = hc.att_policy_id
                        {9} JOIN (
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {7}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = hre.id
                        WHERE hc.state = 'open' AND hre.active = true
                        AND DATE(easl.date) BETWEEN '{0}' AND '{1}'
                        {2} {3} {4} {6} {8}
                        GROUP BY hre.id, hc.att_policy_id
                        ORDER BY hre.name
                    ) main_tbl
                    LEFT JOIN stock_location sl ON sl.id = main_tbl.work_loc_id
                    LEFT JOIN hr_attendance_policy hap ON hap.id = main_tbl.att_policy_id
                    GROUP BY main_tbl.emp_id,main_tbl.emp_name,main_tbl.old_emp_id, main_tbl.device_id, main_tbl.work_loc_id,
                    main_tbl.act_late_days, main_tbl.absent_day, sl.name, main_tbl.is_deduct
                    -- ORDER BY main_tbl.old_emp_id, main_tbl.emp_name
                    ORDER BY {10}, main_tbl.emp_name
                    """.format(start_date, end_date, 
                                work_loc_filter, dept_filter, 
                                emp_filter, deductFilter, 
                                report_type_filter, tags_filter,
                                business_unit_filter, tag_filter_join,
                                order_by
                                )
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        att_sql = """
                    SELECT main_tbl.emp_id, main_tbl.emp_name, main_tbl.date, EXTRACT(DAY FROM (main_tbl.date)) AS day,
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.late_in > 0 AND main_tbl.punch_count = 1 THEN 'LO' ELSE 
                         CASE WHEN main_tbl.status in ('weekend') AND main_tbl.ovt_flag = '0' THEN 'W' ELSE 
                         CASE WHEN main_tbl.status in ('ph') AND main_tbl.ovt_flag ='0' THEN 'PH' ELSE 
                         --CASE WHEN main_tbl.status in ('weekend') AND main_tbl.worked_hours > 0 AND main_tbl.ovt_flag ='1' THEN 'W-OT' ELSE 
                         CASE WHEN main_tbl.status in ('weekend') AND main_tbl.worked_hours > 0 AND main_tbl.ovt_flag ='2' THEN 'W' ELSE 
                         --CASE WHEN main_tbl.status in ('ph') AND main_tbl.worked_hours > 0 AND main_tbl.ovt_flag ='1' THEN 'PH-OT' ELSE 
                         CASE WHEN main_tbl.status in ('ph') AND main_tbl.worked_hours > 0 AND main_tbl.ovt_flag ='2' THEN 'PH' ELSE 
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.diff_time = 0 AND main_tbl.late_in = 0 THEN 'P' ELSE 
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.diff_time = 0 AND main_tbl.late_in = 0 AND main_tbl.ovt_flag ='1' THEN 'P,OT' ELSE 
                         CASE WHEN main_tbl.status = 'ab' THEN 'A' ELSE
                         CASE WHEN main_tbl.status in ('weekend') AND main_tbl.worked_hours > 0 AND hap.work_day_without_week_ph = False THEN 'W,P' ELSE
                         CASE WHEN main_tbl.status in ('ph') AND main_tbl.worked_hours > 0 AND hap.work_day_without_ph = False THEN 'PH,P' ELSE                         
                         CASE WHEN main_tbl.status in ('weekend') AND main_tbl.worked_hours > 0 AND hap.work_day_without_week_ph = True AND main_tbl.ovt_flag ='1' THEN 'OT' ELSE
                         CASE WHEN main_tbl.status in ('ph') AND main_tbl.worked_hours > 0 AND hap.work_day_without_ph = True AND main_tbl.ovt_flag ='1' THEN 'OT' ELSE                         
                         CASE WHEN main_tbl.status = 'weekend' AND (main_tbl.worked_hours = 0 OR main_tbl.worked_hours IS NULL) THEN 'W' ELSE
                         CASE WHEN main_tbl.status = 'ph' AND (main_tbl.worked_hours = 0 OR main_tbl.worked_hours IS NULL) THEN 'PH' ELSE
                         CASE WHEN main_tbl.status = 'leave' THEN leave_tbl.leave_code ELSE
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.diff_time > 0 AND main_tbl.late_in > 0 THEN 'LE' ELSE 
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.late_in > 0 THEN 'L' ELSE 
                         
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.diff_time > 0 THEN 'E' ELSE ''
                         END END END END END END END END END END END END END END END END END END AS status
                    FROM(
                        SELECT tbl1.employee_id AS emp_id, hre.name AS emp_name, hre.id_card_no AS old_emp_id, hc.att_policy_id, tbl1.date, tbl1.day, tbl1.worked_hours, tbl1.late_in, tbl1.diff_time, tbl1.overtime, tbl1.status, tbl1.punch_count, tbl1.ovt_flag
                        FROM (
                            SELECT eatsl.employee_id, eatsl.date, eatsl.day, eatsl.worked_hours, eatsl.late_in, eatsl.diff_time, eatsl.overtime, eatsl.status, eatsl.punch_count, eatsl.ovt_flag
                            FROM employee_attendance_sheet_line eatsl
                            WHERE DATE(date) BETWEEN '{0}' AND '{1}'
                            GROUP BY eatsl.employee_id, eatsl.date, eatsl.day, eatsl.worked_hours, eatsl.late_in, eatsl.diff_time, eatsl.overtime, eatsl.status, eatsl.punch_count, eatsl.ovt_flag
                            ORDER BY eatsl.employee_id, eatsl.date, eatsl.day
                        ) tbl1
                        LEFT JOIN hr_employee hre ON hre.id = tbl1.employee_id
                        LEFT JOIN hr_contract hc ON hc.id = hre.contract_id
                        WHERE hc.state = 'open'
                     	{2} {3} {4} {8}
                        ORDER BY hre.name, tbl1.date
                    ) main_tbl
                    LEFT JOIN (
                        SELECT hld.leave_date, hl.employee_id, hlt.name AS leave_name, hlt.type_code AS leave_code
                        FROM hr_leave hl
                        JOIN hr_leave_details hld ON hld.leave_id = hl.id
                        JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                        WHERE hl.state='validate' AND DATE(hld.leave_date) BETWEEN '{0}' AND '{1}'
                     	{5} {6} {7}
                        ORDER BY hld.leave_date, hl.employee_id
                    ) leave_tbl ON leave_tbl.leave_date = main_tbl.date AND leave_tbl.employee_id = main_tbl.emp_id
                    LEFT JOIN hr_attendance_policy hap ON hap.id = main_tbl.att_policy_id
                    ORDER BY main_tbl.old_emp_id, main_tbl.emp_name, main_tbl.date
                    """.format(start_date, end_date, work_loc_filter, dept_filter, emp_filter, work_loc_filter2,
                               dept_filter2, emp_filter2, report_type_filter)
        self.env.cr.execute(att_sql)
        att_res = self.env.cr.dictfetchall()

        data_list = []
        # master data - master sql data and attendance data list
        for rec in data_res:
            vals = {
                'emp_id': rec['emp_id'],
                'emp_name': rec['emp_name'],
                'old_emp_id': rec['old_emp_id'],
                'loc_name': rec['loc_name'],
                'device_id': rec['device_id'],
                'work_days': rec['no_of_days'],
                'present_days': rec['no_presence'] if not self.is_deducted else (rec['no_presence'] - rec['unpaid_leave_days']),
                'absent_days': rec['no_absence'],
                'late_days': rec['late_days'],
                'early_out': rec['early_days'],
                'leave_days': rec['leave_days'],
                'unpaid_leave_days': rec['unpaid_leave_days'],
                'att_day_list': copy.deepcopy(att_day_list),
                'no_of_days_wph_ot': rec['no_of_days_wph_ot'],
            }
            data_list.append(vals)
        #rec['no_presence'] - rec['unpaid_leave_days'])
        #rec['no_of_days'] - rec['no_absence'] - rec['unpaid_leave_days']

        # updating attendance info
        for rec in data_list:  # master data loop
            emp_id = rec['emp_id']
            att_day_list = rec['att_day_list']
            att_dict = att_day_list[0]
            for rec2 in att_res:  # attendance data loop
                att_emp_id = rec2['emp_id']
                days = str(int(rec2['day'])).zfill(2)
                att = rec2['status']

                # checking whether attendance employee id and master data employee id matches
                if att_emp_id == emp_id:
                    for j in att_dict:  # attendance list loop
                        # checking whether leave type list sequence and leave sequence from leave sql matches
                        if str(j[-2:]) == days:
                            # updating attendance list in master data
                            att_dict[str(j)] = att
                            break

        leave_type_obj = self.env['hr.leave.type'].search([('type_code', '!=', ''), ('year', '=', year)], order='type_code ASC')
        leave_type_names = ",".join(['{0}="{1}"'.format(rec.name, rec.type_code) for rec in leave_type_obj])
        data = {
            'model': "daily.attendance.statistic.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'month': dict(self._fields['month'].selection).get(month),
            'year': year,
            'work_location_name': work_location_name,
            'report_type': dict(self._fields['report_type'].selection).get(report_type),
            'dept_name': dept_name,
            'leave_type_names': leave_type_names,
            'day_list': day_list,
            'week_days': week_days,
            'buisness_unit' : self.sbu_unit_id.display_name if self.sbu_unit_id else "All",
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')) if self.category_ids else 'None Selected',
        }
        return data

    #unused
    def bk_daily_attendance_statistic_report_sql_att(self):
        # m = int(month)
        # y = int(year)
        # ndays = monthrange(y, m)[1]
        start_date = self.start_date
        end_date = self.end_date
        delta = (end_date - start_date).days + 1

        year = self.year
        month = self.month
        user_work_location_id = self.user_work_location_id
        department_ids = self.department_ids
        employee_id = self.employee_id
        report_type = self.report_type

        if delta > 31:
            raise ValidationError('Unable to process due to date range is more than 31 days.')

        date_list = [(start_date + timedelta(days=i)) for i in range(delta)]

        day_list = [i.day for i in date_list]

        week_days = []

        for rec in date_list:
            if rec.weekday() == 0:
                week_days.append('Mon')
            elif rec.weekday() == 1:
                week_days.append('Tue')
            elif rec.weekday() == 2:
                week_days.append('Wed')
            elif rec.weekday() == 3:
                week_days.append('Thu')
            elif rec.weekday() == 4:
                week_days.append('Fri')
            elif rec.weekday() == 5:
                week_days.append('Sat')
            else:
                week_days.append('Sun')

        att_day_list = [{str(rec).replace('-', ''): '' for rec in date_list}]

        work_loc_filter = ""
        work_loc_filter2 = ""
        dept_filter = ""
        dept_filter2 = ""
        emp_filter = ""
        emp_filter2 = ""
        deductFilter = "False"
        work_location_name = "All"
        dept_name = "All"
        report_type_filter = ""
        domain = []

        if user_work_location_id:
            domain += [('user_work_location_id', '=', user_work_location_id.id)]
            work_loc_filter = "AND hre.user_work_location_id = %s" % user_work_location_id.id
            work_loc_filter2 = "AND hl.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if len(department_ids) > 1:
            dept_filter = "AND hre.department_id in {0}".format(tuple(department_ids.ids))
            dept_filter2 = "AND hl.department_id in {0}".format(tuple(department_ids.ids))
            dept_name = ", ".join([d.name for d in department_ids])
        elif len(department_ids) == 1:
            dept_filter = "AND hre.department_id = %s" % department_ids.id
            dept_filter2 = "AND hl.department_id = %s" % department_ids.id
            dept_name = department_ids.name

        if employee_id:
            emp_filter = "AND hre.id = %s" % employee_id.id
            emp_filter2 = "AND hl.employee_id = %s" % employee_id.id

        if self.is_deducted:
            deductFilter = "True"

        if self.report_type == 'current_emp':
            report_type_filter = "AND hre.resigned = False"
        elif self.report_type == 'resign_emp':
            report_type_filter = "AND hre.resigned = True"

        data_sql = """
                    SELECT COALESCE(main_tbl.work_loc_id, 100000) AS user_work_location_id, sl.name AS loc_name,
                    main_tbl.emp_id, main_tbl.old_emp_id, main_tbl.emp_name, main_tbl.device_id,

                    COALESCE(SUM(CASE WHEN hap.work_day_without_week_ph = True THEN main_tbl.no_of_days ELSE 
                    CASE WHEN hap.work_day_without_week_ph = False THEN main_tbl.no_of_days_w ELSE 0 END END)::INT, 0) AS no_of_days,

                    COALESCE(SUM(CASE WHEN hap.work_day_without_week_ph = True THEN main_tbl.no_of_days_wph_ot ELSE 0 END)::INT, 0) AS no_of_days_wph_ot,

                    COALESCE((CASE WHEN main_tbl.is_deduct = False THEN SUM(main_tbl.present_day ) ELSE
                                CASE WHEN main_tbl.is_deduct = True THEN (SUM(CASE WHEN hap.work_day_without_week_ph = True THEN main_tbl.no_of_days ELSE 
                    CASE WHEN hap.work_day_without_week_ph = False THEN main_tbl.no_of_days_w ELSE 0 END END) - (COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0))::INT, 0) + main_tbl.absent_day)) ELSE 0 END END)::INT, 0) AS no_presence,

                    COALESCE((CASE WHEN main_tbl.is_deduct = False THEN SUM(main_tbl.absent_day) ELSE
                                CASE WHEN main_tbl.is_deduct = True THEN COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0))::INT, 0) + main_tbl.absent_day ELSE 0 END END)::INT, 0) AS no_absence,
                    COALESCE((CASE WHEN main_tbl.is_deduct = False THEN SUM(main_tbl.act_late_days) ELSE
                                CASE WHEN main_tbl.is_deduct = True THEN COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0))::INT, 0) ELSE 0 END END)::INT, 0) AS actual_late_count,
                    COALESCE(SUM(CASE WHEN main_tbl.is_deduct = False THEN main_tbl.early_out ELSE
                                 CASE WHEN main_tbl.is_deduct = True THEN main_tbl.early_out/NULLIF(hap.salary_ded_count_early_out, 0) ELSE 0 END END), 0)::INT AS actual_diff_count,
                    COALESCE(SUM(main_tbl.act_late_days), 0)::INT AS late_days,
                    COALESCE(SUM(main_tbl.early_out), 0)::INT AS early_days,
                    (SELECT COUNT(hld.id) AS unpaid_leave_days
                    FROM hr_leave hl
                    JOIN hr_leave_details hld ON hld.leave_id = hl.id
                    JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                    WHERE hl.state='validate' AND hlt.type_code = 'LWP' AND DATE(hld.leave_date) BETWEEN '{0}' AND '{1}' AND hl.employee_id = main_tbl.emp_id),
                    (SELECT COUNT(hld.id) AS leave_days
                    FROM hr_leave hl
                    JOIN hr_leave_details hld ON hld.leave_id = hl.id
                    JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                    WHERE hl.state='validate' AND hlt.type_code != 'LWP' AND DATE(hld.leave_date) BETWEEN '{0}' AND '{1}' AND hl.employee_id = main_tbl.emp_id),
                    COALESCE(SUM(main_tbl.act_late_days/NULLIF(hap.salary_ded_count_late, 0)), 0)::INT AS deduct_abs
                    FROM (
                        SELECT hre.id AS emp_id, hre.name AS emp_name, hre.id_card_no AS old_emp_id, hre.device_user_id AS device_id, hre.user_work_location_id AS work_loc_id, hc.att_policy_id, {5} AS is_deduct,
                        COALESCE(SUM(CASE WHEN easl.late_in > 0 THEN 1 ELSE 0 END), 0) AS act_late_days,
                        COALESCE(SUM(CASE WHEN easl.status = 'ab' THEN 1 ELSE 0 END), 0) AS absent_day,
                        COALESCE(SUM(CASE WHEN easl.pl_sign_in > 0 AND easl.status IS NULL THEN 1 ELSE 0 END), 0) AS present_day,
                        COALESCE(SUM(CASE WHEN easl.diff_time > 0 AND (easl.status IS NULL OR easl.status IN ('weekend', 'ph', 'leave')) THEN 1 ELSE 0 END), 0) AS early_out,

                        COALESCE(SUM(CASE WHEN easl.status in ('ab', 'leave', 'weekend', 'ph') OR easl.status IS NULL THEN 1 ELSE 0 END), 0) AS no_of_days_w,
                        COALESCE(SUM(CASE WHEN easl.status in ('ab', 'leave') OR easl.status IS NULL THEN 1 ELSE 0 END), 0) AS no_of_days,

                        COALESCE(SUM(CASE WHEN easl.status in ('weekend', 'ph') AND easl.worked_hours > 0 AND easl.ovt_flag ='1' THEN 1 ELSE 0 END), 0) AS no_of_days_wph_ot

                        FROM hr_employee hre
                        JOIN hr_contract hc ON hc.employee_id = hre.id
                        JOIN employee_attendance_sheet_line easl ON easl.employee_id = hre.id                        
                        WHERE hc.state = 'open' AND hre.active = true
                        AND DATE(easl.date) BETWEEN '{0}' AND '{1}'
                     	{2} {3} {4} {6}
                        GROUP BY hre.id, hc.att_policy_id
                        ORDER BY hre.name
                    ) main_tbl
                    LEFT JOIN stock_location sl ON sl.id = main_tbl.work_loc_id
                    LEFT JOIN hr_attendance_policy hap ON hap.id = main_tbl.att_policy_id
                    GROUP BY main_tbl.emp_id,main_tbl.emp_name,main_tbl.old_emp_id, main_tbl.device_id, main_tbl.work_loc_id,
                    main_tbl.act_late_days, main_tbl.absent_day, sl.name, main_tbl.is_deduct
                    ORDER BY main_tbl.old_emp_id, main_tbl.emp_name
                    """.format(start_date, end_date, work_loc_filter, dept_filter, emp_filter, deductFilter,
                               report_type_filter)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        att_sql = """
                    SELECT main_tbl.emp_id, main_tbl.emp_name, main_tbl.date, EXTRACT(DAY FROM (main_tbl.date)) AS day,
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.late_in > 0 AND main_tbl.punch_count = 1 THEN 'LO' ELSE 
                         CASE WHEN main_tbl.status in ('weekend') AND main_tbl.ovt_flag = '0' THEN 'W' ELSE 
                         CASE WHEN main_tbl.status in ('ph') AND main_tbl.ovt_flag ='0' THEN 'PH' ELSE 
                         --CASE WHEN main_tbl.status in ('weekend') AND main_tbl.worked_hours > 0 AND main_tbl.ovt_flag ='1' THEN 'W-OT' ELSE 
                         CASE WHEN main_tbl.status in ('weekend') AND main_tbl.worked_hours > 0 AND main_tbl.ovt_flag ='2' THEN 'W' ELSE 
                         --CASE WHEN main_tbl.status in ('ph') AND main_tbl.worked_hours > 0 AND main_tbl.ovt_flag ='1' THEN 'PH-OT' ELSE 
                         CASE WHEN main_tbl.status in ('ph') AND main_tbl.worked_hours > 0 AND main_tbl.ovt_flag ='2' THEN 'PH' ELSE 
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.diff_time = 0 AND main_tbl.late_in = 0 THEN 'P' ELSE 
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.diff_time = 0 AND main_tbl.late_in = 0 AND main_tbl.ovt_flag ='1' THEN 'P,OT' ELSE 
                         CASE WHEN main_tbl.status = 'ab' THEN 'A' ELSE
                         CASE WHEN main_tbl.status in ('weekend') AND main_tbl.worked_hours > 0 AND hap.work_day_without_week_ph = False THEN 'W,P' ELSE
                         CASE WHEN main_tbl.status in ('ph') AND main_tbl.worked_hours > 0 AND hap.work_day_without_ph = False THEN 'PH,P' ELSE                         
                         CASE WHEN main_tbl.status in ('weekend') AND main_tbl.worked_hours > 0 AND hap.work_day_without_week_ph = True AND main_tbl.ovt_flag ='1' THEN 'OT' ELSE
                         CASE WHEN main_tbl.status in ('ph') AND main_tbl.worked_hours > 0 AND hap.work_day_without_ph = True AND main_tbl.ovt_flag ='1' THEN 'OT' ELSE                         
                         CASE WHEN main_tbl.status = 'weekend' AND (main_tbl.worked_hours = 0 OR main_tbl.worked_hours IS NULL) THEN 'W' ELSE
                         CASE WHEN main_tbl.status = 'ph' AND (main_tbl.worked_hours = 0 OR main_tbl.worked_hours IS NULL) THEN 'PH' ELSE
                         CASE WHEN main_tbl.status = 'leave' THEN leave_tbl.leave_code ELSE
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.diff_time > 0 AND main_tbl.late_in > 0 THEN 'LE' ELSE 
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.late_in > 0 THEN 'L' ELSE 
                         
                         CASE WHEN main_tbl.status IS NULL AND main_tbl.diff_time > 0 THEN 'E' ELSE ''
                         END END END END END END END END END END END END END END END END END END AS status
                    FROM(
                        SELECT tbl1.employee_id AS emp_id, hre.name AS emp_name, hre.id_card_no AS old_emp_id, hc.att_policy_id, tbl1.date, tbl1.day, tbl1.worked_hours, tbl1.late_in, tbl1.diff_time, tbl1.overtime, tbl1.status, tbl1.punch_count, tbl1.ovt_flag
                        FROM (
                            SELECT eatsl.employee_id, eatsl.date, eatsl.day, eatsl.worked_hours, eatsl.late_in, eatsl.diff_time, eatsl.overtime, eatsl.status, eatsl.punch_count, eatsl.ovt_flag
                            FROM employee_attendance_sheet_line eatsl
                            WHERE DATE(date) BETWEEN '{0}' AND '{1}'
                            GROUP BY eatsl.employee_id, eatsl.date, eatsl.day, eatsl.worked_hours, eatsl.late_in, eatsl.diff_time, eatsl.overtime, eatsl.status, eatsl.punch_count, eatsl.ovt_flag
                            ORDER BY eatsl.employee_id, eatsl.date, eatsl.day
                        ) tbl1
                        LEFT JOIN hr_employee hre ON hre.id = tbl1.employee_id
                        LEFT JOIN hr_contract hc ON hc.id = hre.contract_id
                        WHERE hc.state = 'open'
                     	{2} {3} {4} {8}
                        ORDER BY hre.name, tbl1.date
                    ) main_tbl
                    LEFT JOIN (
                        SELECT hld.leave_date, hl.employee_id, hlt.name AS leave_name, hlt.type_code AS leave_code
                        FROM hr_leave hl
                        JOIN hr_leave_details hld ON hld.leave_id = hl.id
                        JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                        WHERE hl.state='validate' AND DATE(hld.leave_date) BETWEEN '{0}' AND '{1}'
                     	{5} {6} {7}
                        ORDER BY hld.leave_date, hl.employee_id
                    ) leave_tbl ON leave_tbl.leave_date = main_tbl.date AND leave_tbl.employee_id = main_tbl.emp_id
                    LEFT JOIN hr_attendance_policy hap ON hap.id = main_tbl.att_policy_id
                    ORDER BY main_tbl.old_emp_id, main_tbl.emp_name, main_tbl.date
                    """.format(start_date, end_date, work_loc_filter, dept_filter, emp_filter, work_loc_filter2,
                               dept_filter2, emp_filter2, report_type_filter)
        self.env.cr.execute(att_sql)
        att_res = self.env.cr.dictfetchall()

        data_list = []
        # master data - master sql data and attendance data list
        for rec in data_res:
            vals = {
                'emp_id': rec['emp_id'],
                'emp_name': rec['emp_name'],
                'old_emp_id': rec['old_emp_id'],
                'loc_name': rec['loc_name'],
                'device_id': rec['device_id'],
                'work_days': rec['no_of_days'],
                'present_days': rec['no_presence'] if not self.is_deducted else (
                            rec['no_presence'] - rec['unpaid_leave_days']),
                'absent_days': rec['no_absence'],
                'late_days': rec['late_days'],
                'early_out': rec['early_days'],
                'leave_days': rec['leave_days'],
                'unpaid_leave_days': rec['unpaid_leave_days'],
                'att_day_list': copy.deepcopy(att_day_list),
                'no_of_days_wph_ot': rec['no_of_days_wph_ot'],
            }
            data_list.append(vals)
        # rec['no_presence'] - rec['unpaid_leave_days'])
        # rec['no_of_days'] - rec['no_absence'] - rec['unpaid_leave_days']

        # updating attendance info
        for rec in data_list:  # master data loop
            emp_id = rec['emp_id']
            att_day_list = rec['att_day_list']
            att_dict = att_day_list[0]
            for rec2 in att_res:  # attendance data loop
                att_emp_id = rec2['emp_id']
                days = str(int(rec2['day'])).zfill(2)
                att = rec2['status']

                # checking whether attendance employee id and master data employee id matches
                if att_emp_id == emp_id:
                    for j in att_dict:  # attendance list loop
                        # checking whether leave type list sequence and leave sequence from leave sql matches
                        if str(j[-2:]) == days:
                            # updating attendance list in master data
                            att_dict[str(j)] = att
                            break

        leave_type_obj = self.env['hr.leave.type'].search([('type_code', '!=', ''), ('year', '=', year)],
                                                          order='type_code ASC')
        leave_type_names = ",".join(['{0}="{1}"'.format(rec.name, rec.type_code) for rec in leave_type_obj])
        data = {
            'model': "daily.attendance.statistic.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'month': dict(self._fields['month'].selection).get(month),
            'year': year,
            'work_location_name': work_location_name,
            'report_type': dict(self._fields['report_type'].selection).get(report_type),
            'dept_name': dept_name,
            'leave_type_names': leave_type_names,
            'day_list': day_list,
            'week_days': week_days,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data
