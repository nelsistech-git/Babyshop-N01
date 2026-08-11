from odoo import fields, models, api, _
from calendar import monthrange
from datetime import datetime
from datetime import date
from itertools import groupby

import xlsxwriter

import base64
from io import BytesIO


class OneTimePunchSummaryReportWizard(models.TransientModel):
    _name = "one.time.punch.summary.report.wizard"
    _description = "One Time Punch Summary Report Wizard"

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

    file_data = fields.Binary('One Time Punch Summary Report Wizard')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', default=lambda self: self._get_work_loc(), domain=lambda self: self._set_domain_work_loc())
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

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

    type = fields.Selection([
        ('01', 'Summary'),
        ('02', 'Detail')
    ], string='Type', required=True, default= '01')

    category_ids = fields.Many2many('hr.employee.category', 'one_time_punch_summary_employee_category_rel', 
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

    # summary excel ========
    def one_time_punch_summary_report_excel(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        work_location_id = self.user_work_location_id

        # get data from sql
        data = self.one_time_punch_summary_report_sql_summary(month, year, department_id, work_location_id)

        file_name = "One Time Punch Summary Report (%s - %s).xlsx" % (data['month'], data['year'])
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

        for line in data['csr']:
            for line2 in line:
                sheet = workbook.add_worksheet(line[line2][0]['location_name'])

                sheet.merge_range(0, 0, 0, 5, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 2, 5,
                                  "One Time Punch Summary Report (%s - %s)" % (data['month'], data['year']),
                                  format0)

                sheet.merge_range(3, 0, 3, 1, 'Work/Job Location: {0}'.format(line[line2][0]['location_name']), format1)
                sheet.merge_range(3, 2, 3, 3, 'Department Name: {0}'.format(data['dept_name']), format1)
                sheet.write(3, 4, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
                sheet.write(3, 5, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: None Selected", format1)



                sheet.write(4, 0, 'Employee ID No', format1)
                sheet.write(4, 1, 'Employee Name', format1)
                sheet.write(4, 2, 'Department', format1)
                sheet.write(4, 3, 'Designation', format1)
                sheet.write(4, 4, 'One Time Punch Days', format2)
                sheet.write(4, 5, 'Total Days', format2)

                row = 5
                col = 0

                for line3 in line[line2]:
                    sheet.write(row, col, line3['emp_id_card'], format4)
                    sheet.write(row, col + 1, line3['employee_name'], format4)
                    sheet.write(row, col + 2, line3['department_name'], format4)
                    sheet.write(row, col + 3, line3['designation_name'], format4)
                    sheet.write(row, col + 4, line3['punch_days'], format5)
                    sheet.write(row, col + 5, line3['one_time_punch'], format5)

                    row = row + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'One Time Punch Summary Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=one.time.punch.summary.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    # summary pdf ========
    def one_time_punch_summary_report_pdf(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        work_location_id = self.user_work_location_id

        # get data from sql
        data = self.one_time_punch_summary_report_sql_summary(month, year, department_id, work_location_id)

        return self.env.ref(
            'custom_hr_report.one_time_punch_summary_report_tmpl').with_context(landscape=True).report_action(self,
                                                                                                              data=data)

    # summary fun ========
    def one_time_punch_summary_report_sql_summary(self, month, year, department_id, work_location_id):
        m = int(month)
        y = int(year)
        ndays = monthrange(y, m)[1]
        start_date = date(y, m, 1)
        end_date = date(y, m, ndays)

        dept_filter = ""
        work_loc_filter = ""
        dept_name = "All"
        work_location_name = "All"
        tags_filter = ""
        tag_filter_join = "LEFT"
        business_unit_filter = ""

        order_by = "hr.name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "hr.id_card_no"
        print("summary",order_by)


        if department_id:
            dept_filter = "AND hr.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if work_location_id:
            work_loc_filter = "AND hr.user_work_location_id = %s" % work_location_id.id
            work_location_name = work_location_id.display_name
                
        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])                                        
                                        
        if self.sbu_unit_id:
            business_unit_filter = "AND hr.sbu_unit_id = {0}".format(self.sbu_unit_id.id)

        #ha.worked_hours < 1
        data_sql = """
                    SELECT hr.name AS employee_name, hj.name->>'en_US' AS designation_name, hr.id_card_no AS emp_id_card, COALESCE(hr.user_work_location_id, 100000) AS user_work_location_id,
                    hd.name->>'en_US' AS department_name, COUNT(ha.worked_hours) AS one_time_punch, sl.name AS location_name,
                    array_to_string(array_agg(CASE WHEN ha.punch_count = 1 THEN EXTRACT(DAY FROM ha.attendance_date)  ELSE NULL END), ', ')  AS punch_days 
                    FROM hr_attendance ha
                    JOIN hr_employee hr ON hr.id = ha.employee_id
                    LEFT JOIN hr_job hj ON hj.id = hr.job_id
                    LEFT JOIN stock_location sl ON sl.id = hr.user_work_location_id
                    LEFT JOIN hr_department hd ON hd.id = hr.department_id
                    {6} JOIN (
                        SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                        JOIN hr_employee_category etag on etag.id=ecr.category_id
                        {5}
                        GROUP BY emp_id
                    ) emp_tag ON emp_tag.emp_id = hr.id
                    WHERE ha.punch_count = 1 AND DATE(ha.attendance_date) BETWEEN '{0}' and '{1}' {2} {3} {4}
                    GROUP BY hr.name, hj.name, hr.id_card_no, hd.name, hr.user_work_location_id, sl.name
                    -- ORDER BY hr.id_card_no, hr.name
                    ORDER BY {7}, hr.name
                    """.format(start_date, end_date, 
                                dept_filter, work_loc_filter,
                                business_unit_filter, tags_filter,
                                tag_filter_join, order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()
        data_list = []

        for d in data_res:
            punch_days = ''
            if d['punch_days']:
                punch_days = ', '.join(map(str, sorted(list(map(int, d['punch_days'].split(', '))))))
            vals = {
                'employee_name': d['employee_name'],
                'designation_name': d['designation_name'],
                'emp_id_card': d['emp_id_card'],
                'user_work_location_id': d['user_work_location_id'],
                'location_name': d['location_name'],
                'department_name': d['department_name'],
                'punch_days': punch_days,
                'one_time_punch': d['one_time_punch'],
            }
            data_list.append(vals)

        # define a function for key
        def key_func(k):
            return k['user_work_location_id']

        data_list = sorted(data_list, key=key_func)

        final_data_list = []

        for key, value in groupby(data_list, key_func):
            vals = {
                key: list(value)
            }
            final_data_list.append(vals)

        data = {
            'model': "one.time.punch.summary.report.wizard",
            'form': self.read()[0],
            'csr': final_data_list,
            'month': dict(self._fields['month'].selection).get(self.month),
            'year': year,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data

    # detail excel ========
    def one_time_punch_summary_report_excel_detail(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        work_location_id = self.user_work_location_id

        # get data from sql
        data = self.one_time_punch_summary_report_sql_detail(month, year, department_id, work_location_id)

        file_name = "One Time Punch Summary Report (%s - %s).xlsx" % (data['month'], data['year'])
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

        sheet.merge_range(0, 0, 0, 6, "{0}".format(data['form']['company_id'][1]), format0)
        sheet.merge_range(1, 0, 2, 6,
                          "One Time Punch Detail Report (%s - %s)" % (data['month'], data['year']),
                          format0)

        # sheet.merge_range(3, 0, 3, 2, 'Work/Job Location: {0}'.format(line[line2][0]['location_name']), format1)
        sheet.merge_range(3, 0, 3, 1, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
        sheet.merge_range(3, 2, 3, 3, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: None Selected", format1)
        sheet.merge_range(3, 4, 3, 6, 'Department Name: {0}'.format(data['dept_name']), format1)

        sheet.write(4, 0, 'Branch', format1)
        sheet.write(4, 1, 'Employee ID No', format1)
        sheet.write(4, 2, 'Employee Name', format1)
        sheet.write(4, 3, 'Department', format1)
        sheet.write(4, 4, 'Designation', format1)
        sheet.write(4, 5, 'Days', format2)
        sheet.write(4, 6, 'In Time', format2)

        row = 5
        col = 0
        for line in data['csr']:
            sheet.write(row, col, line['location_name'], format4)
            sheet.write(row, col + 1, line['emp_id_card'], format4)
            sheet.write(row, col + 2, line['employee_name'], format4)
            sheet.write(row, col + 3, line['department_name'], format4)
            sheet.write(row, col + 4, line['designation_name'], format4)
            # sheet.write(row, col + 4, line['punch_days'], format5)
            sheet.write(row, col + 5, line['one_time_punch'], format5)
            sheet.write(row, col + 6, '', format5)
            row = row + 1
            for line2 in line['detail_list']:
                if line2['punch_days']:
                    sheet.write(row, col + 5, datetime.strptime(line2['punch_days'].strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S').strftime('%d-%b-%y'), format4)
                else:
                    sheet.write(row, col + 5, line2['punch_days'], format5)
                sheet.write(row, col + 5, datetime.strptime(line2['check_in'].strftime('%H:%M:%S'), '%H:%M:%S').strftime('%h-%m-%s'), format4)

                # sheet.write(row, col + 6, line2['check_in'], format5)
                row = row + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'One Time Punch Summary Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=one.time.punch.summary.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    # detail pdf ========
    def one_time_punch_summary_report_pdf_detail(self):
        year = self.year
        month = self.month
        department_id = self.department_id
        work_location_id = self.user_work_location_id

        # get data from sql
        data = self.one_time_punch_summary_report_sql_detail(month, year, department_id, work_location_id)

        return self.env.ref(
            'custom_hr_report.one_time_punch_detail_report_tmpl').with_context(landscape=True).report_action(self,
                                                                                                              data=data)

    # detail fun ========
    def one_time_punch_summary_report_sql_detail(self, month, year, department_id, work_location_id):
        m = int(month)
        y = int(year)
        ndays = monthrange(y, m)[1]
        start_date = date(y, m, 1)
        end_date = date(y, m, ndays)

        dept_filter = ""
        work_loc_filter = ""
        dept_name = "All"
        work_location_name = "All"
        tags_filter = ""
        tag_filter_join = "LEFT"
        business_unit_filter = ""

        order_by = "hr.name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "hr.id_card_no"
        print("details",order_by)



        if department_id:
            dept_filter = "AND hr.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if work_location_id:
            work_loc_filter = "AND hr.user_work_location_id = %s" % work_location_id.id
            work_location_name = work_location_id.display_name

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])  
                                        
        if self.sbu_unit_id:
            business_unit_filter = "AND hr.sbu_unit_id = {0}".format(self.sbu_unit_id.id)

        #ha.worked_hours < 1
        data_sql = """
                    SELECT hr.id as hr_id,  hr.name AS employee_name, hj.name->>'en_US' AS designation_name, hr.id_card_no AS emp_id_card, COALESCE(hr.user_work_location_id, 100000) AS work_location_id,
                    hd.name->>'en_US' AS department_name, sl.name AS location_name, COUNT(ha.worked_hours) AS one_time_punch
                    FROM hr_attendance ha
                    JOIN hr_employee hr ON hr.id = ha.employee_id
                    LEFT JOIN hr_job hj ON hj.id = hr.job_id
                    LEFT JOIN stock_location sl ON sl.id = hr.user_work_location_id
                    LEFT JOIN hr_department hd ON hd.id = hr.department_id
                    {6} JOIN (
                        SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                        JOIN hr_employee_category etag on etag.id=ecr.category_id
                        {5}
                        GROUP BY emp_id
                    ) emp_tag ON emp_tag.emp_id = hr.id
                    WHERE ha.punch_count = 1 AND DATE(ha.attendance_date) BETWEEN '{0}' and '{1}' {2} {3} {4}
                    GROUP BY hr.name, hj.name, hr.id_card_no, hd.name, hr.user_work_location_id, sl.name, hr.id
                    -- ORDER BY hr.id_card_no, hr.name
                    ORDER BY {7}, hr.name
                    """.format(start_date, end_date,
                                dept_filter, work_loc_filter,
                                business_unit_filter, tags_filter, 
                                tag_filter_join, order_by)
        self.env.cr.execute(data_sql)
        single_res = self.env.cr.dictfetchall()
        for rec in single_res:
            data_sql = """
                        SELECT ha.attendance_date  AS punch_days, check_in::TIME as check_in
                        FROM hr_attendance ha
                        JOIN hr_employee hr ON hr.id = ha.employee_id
                        WHERE ha.punch_count = 1 AND DATE(ha.attendance_date) BETWEEN '{0}' and '{1}' {2} {3} and hr.id = {4}
                        ORDER BY hr.id_card_no, hr.name
                        """.format(start_date, end_date, dept_filter, work_loc_filter, rec['hr_id'])
            self.env.cr.execute(data_sql)
            detail_res = self.env.cr.dictfetchall()
            # print("detail_res",detail_res)
            if detail_res:
                rec['detail_list'] = detail_res

        print("single_res",single_res)
        # print(data_sql)

        print("self.read()[0]",self.read()[0])
        data = {
            'model': "one.time.punch.summary.report.wizard",
            'form': self.read()[0],
            'csr': single_res,
            'month': dict(self._fields['month'].selection).get(self.month),
            'year': year,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data
