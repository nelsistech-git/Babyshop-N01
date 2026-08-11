from odoo import fields, models, api, _
import datetime
from calendar import monthrange
from datetime import date, datetime
import copy
from itertools import groupby

import xlsxwriter

import base64
from io import BytesIO


class YearlyLeaveSummaryReportWizard(models.TransientModel):
    _name = "yearly.leave.summary.report.wizard"
    _description = "Yearly Leave Summary Report Wizard"

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

    file_data = fields.Binary('Yearly Leave Summary Report Wizard')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    # start_date = fields.Date(string='Start Date')
    # end_date = fields.Date(string='End Date')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                            default=lambda self: self._get_work_loc(),
                                            domain=lambda self: self._set_domain_work_loc())
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')

    category_ids = fields.Many2many('hr.employee.category', 'yearly_leave_summary_employee_category_rel', 
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

    # @api.constrains('year', 'start_date', 'end_date')
    # def date_constrains(self):
    #     start_date_year = datetime.strptime(str(self.start_date), '%Y-%m-%d').strftime('%Y')
    #     end_date_year = datetime.strptime(str(self.end_date), '%Y-%m-%d').strftime('%Y')
    #     if self.end_date < self.start_date:
    #         raise ValidationError(_('Start date cannot be greater than the end date.'))
    #
    #     if start_date_year != end_date_year != self.year:
    #         raise ValidationError(_('Start date and end date must be of the year %s.') % self.year)

    def yearly_leave_summary_report_pdf(self):
        year = self.year
        # company_id = self.company_id
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        # get data from sql
        data = self.yearly_leave_summary_report_sql(year, user_work_location_id, department_id, employee_id)

        return self.env.ref(
            'custom_hr_leave.yearly_leave_report_tmpl').with_context(landscape=True).report_action(self, data=data)

    def yearly_leave_summary_report_excel(self):
        year = self.year
        # start_date = self.start_date
        # end_date = self.end_date
        # company_id = self.company_id
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        # get data from sql
        data = self.yearly_leave_summary_report_sql(year, user_work_location_id, department_id, employee_id)

        # start_date = datetime.strptime(str(start_date), '%Y-%m-%d').strftime('%d-%b-%Y')
        # end_date = datetime.strptime(str(end_date), '%Y-%m-%d').strftime('%d-%b-%Y')

        file_name = "Yearly Leave Summary Report (%s).xlsx" % (year)
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
                sheet = workbook.add_worksheet(line[line2][0]['loc_name'])

                leave_type_list = data['leave_type_list']

                # heading start
                main_head_col = 5 + (len(leave_type_list) * 2) + (len(leave_type_list) * 12)

                sheet.merge_range(0, 0, 0, main_head_col, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 1, main_head_col, "Yearly Leave Summary Report", format0)
                sheet.merge_range(2, 0, 2, main_head_col, "For the year of %s" % (year), format0)

                # sheet.merge_range(3, 0, 3, int(main_head_col / 2),'Work/Job Location: {0}'.format(line[line2][0]['loc_name']), format1)
                # sheet.merge_range(3, int(main_head_col / 2) + 1, 3, main_head_col,'Department Name: {0}'.format(data['dept_name']), format3)
                
                work_job_location_end_col = int((main_head_col + 2) / 4)
                department_name_start_col = work_job_location_end_col + 1
                department_name_end_col = int((main_head_col + 2) / 2)
                office_unit_start_col = department_name_end_col + 1
                office_unit_end_col = office_unit_start_col + int((main_head_col + 2) / 4) - 1
                tags_start_col = office_unit_end_col + 1
                tags_end_col = main_head_col

                # Merge for Work/Job Location
                sheet.merge_range(
                    3, 0, 3, work_job_location_end_col,
                    'Work/Job Location: {0}'.format(line[line2][0]['loc_name']), format1
                )

                # Merge for Department Name
                sheet.merge_range(
                    3, department_name_start_col, 3, department_name_end_col,
                    'Department Name: {0}'.format(data['dept_name']), format1
                )

                # Merge for Office/Business Unit
                sheet.merge_range(
                    3, office_unit_start_col, 3, office_unit_end_col,
                    'Office/Business Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Business Unit: All", format1
                )

                # Merge for Tags
                sheet.merge_range(
                    3, tags_start_col, 3, tags_end_col,
                    'Tags: {0}'.format(', '.join(self.category_ids.mapped('display_name'))) if self.category_ids else "Tags: None Selected", format1
                )

                
                
                
                # heading end

                sheet.merge_range(4, 0, 5, 0, 'Sl. No.', format1)
                sheet.merge_range(4, 1, 5, 1, 'Employee ID', format1)
                sheet.merge_range(4, 2, 5, 2, 'Employee Name', format1)
                sheet.merge_range(4, 3, 5, 3, 'Work/Job Location', format1)
                sheet.merge_range(4, 4, 5, 4, 'Department', format2)
                sheet.merge_range(4, 5, 5, 5, 'Designation', format2)

                head_col = 6

                if (len(leave_type_list) - 1) > 0:
                    sheet.merge_range(4, head_col, 4, head_col + (len(leave_type_list) - 1), 'Allowable Leave', format2)
                else:
                    sheet.write(4, head_col, 'Allowable Leave', format2)

                for alw_rec in range(len(leave_type_list)):
                    sheet.write(5, head_col, leave_type_list[alw_rec]['leave_name'], format2)

                    head_col = head_col + 1

                head_col2 = head_col

                for leave_rec in range(len(leave_type_list)):
                    sheet.merge_range(4, head_col2, 4, head_col2 + 11,
                                      'Total {0} {1}'.format(leave_type_list[leave_rec]['leave_name'], data['year']),
                                      format2)

                    head_col2 = head_col2 + 12

                head_col3 = head_col

                for i in range(len(leave_type_list)):
                    sheet.write(5, head_col3, 'Jan', format2)
                    sheet.write(5, head_col3 + 1, 'Feb', format2)
                    sheet.write(5, head_col3 + 2, 'Mar', format2)
                    sheet.write(5, head_col3 + 3, 'Apr', format2)
                    sheet.write(5, head_col3 + 4, 'May', format2)
                    sheet.write(5, head_col3 + 5, 'Jun', format2)
                    sheet.write(5, head_col3 + 6, 'Jul', format2)
                    sheet.write(5, head_col3 + 7, 'Aug', format2)
                    sheet.write(5, head_col3 + 8, 'Sep', format2)
                    sheet.write(5, head_col3 + 9, 'Oct', format2)
                    sheet.write(5, head_col3 + 10, 'Nov', format2)
                    sheet.write(5, head_col3 + 11, 'Dec', format2)

                    head_col3 = head_col3 + 12

                head_col4 = head_col3

                if (len(leave_type_list) - 1) > 0:
                    sheet.merge_range(4, head_col4, 4, head_col4 + (len(leave_type_list) - 1), 'Balance Leave', format2)
                else:
                    sheet.write(4, head_col4, 'Balance Leave', format2)

                # sheet.merge_range(4, head_col4, 4, head_col4 + (len(leave_type_list) - 1), 'Balance Leave', format2)

                for bl_rec in range(len(leave_type_list)):
                    sheet.write(5, head_col4, leave_type_list[bl_rec]['leave_name'], format2)

                    head_col4 = head_col4 + 1

                # excel body
                row = 6
                col = 0
                type_col = 6

                sl_no = 1

                for line3 in line[line2]:
                    sheet.write(row, col, sl_no, format5)
                    sheet.write(row, col + 1, line3['emp_name'], format4)
                    sheet.write(row, col + 2, line3['old_emp_id'], format4)
                    sheet.write(row, col + 3, line3['loc_name'], format4)
                    sheet.write(row, col + 4, line3['dept_name'], format4)
                    sheet.write(row, col + 5, line3['job_name'], format4)

                    for j in line3['leave_types']:
                        sheet.write(row, type_col, j['alloc_count'], format5)

                        type_col = type_col + 1

                    for k in line3['leave_types']:
                        sheet.write(row, type_col, k['1'], format5)
                        sheet.write(row, type_col + 1, k['2'], format5)
                        sheet.write(row, type_col + 2, k['3'], format5)
                        sheet.write(row, type_col + 3, k['4'], format5)
                        sheet.write(row, type_col + 4, k['5'], format5)
                        sheet.write(row, type_col + 5, k['6'], format5)
                        sheet.write(row, type_col + 6, k['7'], format5)
                        sheet.write(row, type_col + 7, k['8'], format5)
                        sheet.write(row, type_col + 8, k['9'], format5)
                        sheet.write(row, type_col + 9, k['10'], format5)
                        sheet.write(row, type_col + 10, k['11'], format5)
                        sheet.write(row, type_col + 11, k['12'], format5)

                        type_col = type_col + 12

                    for l in line3['leave_types']:
                        sheet.write(row, type_col, l['leave_remain'], format5)

                        type_col = type_col + 1

                    row = row + 1
                    sl_no = sl_no + 1
                    type_col = 6

        workbook.close()
        file_pointer.seek(0)
        # file_data = base64.encodestring(file_pointer.read())
        # file_data = base64.encodebytes(file_pointer.read())
        file_data = base64.b64encode(file_pointer.read())

        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Yearly Leave Summary Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=yearly.leave.summary.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def yearly_leave_summary_report_sql(self, year, user_work_location_id, department_id, employee_id):
        y = int(year)
        ndays = monthrange(y, 12)[1]
        start_date = date(y, 1, 1)
        end_date = date(y, 12, ndays)

        work_loc_filter = ""
        dept_filter = ""
        emp_filter = ""
        work_location_name = "All"
        dept_name = "All"
        filter = ""
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "emp_tbl.em_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "emp_tbl.old_emp_id"
        # print(order_by)


        if user_work_location_id:
            work_loc_filter = "AND emp_tbl.user_work_location_id = %s " % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if department_id:
            dept_filter = "AND hd.id = %s " % department_id.id
            dept_name = department_id.display_name

        if employee_id:
            emp_filter = "AND emp_tbl.emp_id = %s " % employee_id.id

        if any([user_work_location_id, department_id, employee_id]):
            filter = "WHERE" + work_loc_filter + dept_filter + emp_filter
            filter = filter.replace('AND', '', 1)

        leave_type_obj = self.env['hr.leave.type'].search([('year', '=', str(y))], order="sequence ASC")

        leave_type_list = []

        # leave types list
        for rec in leave_type_obj:
            leave_name = rec.display_name
            leave_seq = str(rec.sequence)
            jan = 0
            feb = 0
            mar = 0
            apr = 0
            may = 0
            jun = 0
            jul = 0
            aug = 0
            sep = 0
            oct = 0
            nov = 0
            dec = 0
            alloc_count = 0
            leave_remain = 0
            vals = {
                'leave_seq': leave_seq,
                'leave_name': leave_name,
                'alloc_count': alloc_count,
                '1': jan,
                '2': feb,
                '3': mar,
                '4': apr,
                '5': may,
                '6': jun,
                '7': jul,
                '8': aug,
                '9': sep,
                '10': oct,
                '11': nov,
                '12': dec,
                'leave_remain': leave_remain
            }
            leave_type_list.append(vals)

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "WHERE hre.sbu_unit_id = {0}".format(self.sbu_unit_id.id)  


        # master sql - employee info
        data_sql = """
                    SELECT emp_tbl.emp_id AS emp_id, stl.name AS loc_name, COALESCE(emp_tbl.user_work_location_id, 100000) AS user_work_location_id, emp_tbl.old_emp_id AS old_emp_id, emp_tbl.em_name AS emp_name, hd.name->>'en_US' AS dept_name, hj.name->>'en_US' AS job_name
                    FROM (
                        SELECT hre.id AS emp_id, hre.user_work_location_id AS user_work_location_id, hre.name AS emp_name, hre.id_card_no AS old_emp_id, 
                            hre.name AS em_name, hre.department_id AS dept_id, hre.job_id AS job_id
                        FROM hr_employee hre
                        JOIN (SELECT DISTINCT(employee_id) AS employee_id FROM hr_leave_allocation
                        WHERE state='validate') alo ON hre.id = alo.employee_id
                        {3} JOIN (
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {2}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = hre.id
                            {1}
                    ) emp_tbl
                    LEFT JOIN hr_department AS hd on hd.id = emp_tbl.dept_id
                    LEFT JOIN hr_job hj ON hj.id = emp_tbl.job_id
                    LEFT JOIN stock_location stl ON stl.id = emp_tbl.user_work_location_id
                    {0}
                    -- ORDER BY emp_tbl.old_emp_id, emp_tbl.em_name
                    ORDER BY {4}, emp_tbl.em_name
                    """.format(filter, business_unit_filter,
                                tags_filter, tag_filter_join, 
                                order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        # leave info sql - allocate, leave
        leave_sql = """
                        SELECT tbl1.emp_id, tbl2.leave_month::INT, tbl1.sequence, COALESCE(tbl1.alloc_count, 0) AS alloc_count, COALESCE(tbl2.leave_count, 0) AS leave_count
                        FROM(
                            SELECT hlt.sequence AS sequence, hla.employee_id AS emp_id, hla.number_of_days AS alloc_count
                            FROM hr_leave_type hlt
                            LEFT JOIN hr_leave_allocation hla ON hla.holiday_status_id = hlt.id
                            WHERE hla.state='validate' AND hlt.active='True' AND hlt.year = '{0}'
                            GROUP BY hlt.id, hlt.sequence, hla.id, hla.number_of_days
                            ORDER BY hlt.sequence
                            ) tbl1
                        LEFT JOIN (
                            SELECT EXTRACT(MONTH FROM (hld.leave_date)) AS leave_month, leave_tbl.sequence, leave_tbl.emp_id, COALESCE(SUM(hld.leave_no), 0) AS leave_count
                            FROM (
                                    SELECT hl.id AS leave_id, hlt.sequence AS sequence, hl.employee_id AS emp_id
                                    FROM hr_leave hl
                                    LEFT JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                                    WHERE hl.state='validate'
                                    AND DATE(hl.request_date_to) BETWEEN '{1}' AND '{2}'
                                    GROUP BY hl.id, hlt.sequence, hl.employee_id
                                ) leave_tbl
                            LEFT JOIN hr_leave_details hld ON hld.leave_id = leave_tbl.leave_id
                            WHERE DATE(hld.leave_date) BETWEEN '{1}' AND '{2}'
                            GROUP BY EXTRACT(MONTH FROM (hld.leave_date)), leave_tbl.sequence, leave_tbl.emp_id
                            ORDER BY leave_tbl.sequence
                            ) tbl2 ON (tbl2.emp_id = tbl1.emp_id AND tbl2.sequence = tbl1.sequence)
                        ORDER BY tbl1.emp_id, tbl1.sequence
                        """.format(y, start_date, end_date)
        self.env.cr.execute(leave_sql)
        leave_res = self.env.cr.dictfetchall()
        # --------------------
        data_list = []

        # master data - master sql data and leave type list merge
        for rec in data_res:
            vals = {
                'emp_id': rec['emp_id'],
                'emp_name': rec['emp_name'],
                'old_emp_id': rec['old_emp_id'],
                'loc_name': rec['loc_name'],
                'user_work_location_id': rec['user_work_location_id'],
                'dept_name': rec['dept_name'],
                'job_name': rec['job_name'],
                'leave_types': copy.deepcopy(leave_type_list)
            }
            data_list.append(vals)

        # updating leave info
        for rec in data_list:  # master data loop
            emp_id = rec['emp_id']
            leave_types_list = rec['leave_types']
            for rec2 in leave_res:  # leave data loop
                leave_emp_id = rec2['emp_id']
                leave_seq = str(rec2['sequence'])
                leave_alloc_count = rec2['alloc_count']

                leave_month = rec2['leave_month']
                leave_leave_count = rec2['leave_count']

                # checking whether leave employee id and master data employee id matches
                if leave_emp_id == emp_id:
                    for j in range(len(leave_types_list)):  # leave type list loop
                        type_dict = leave_types_list[j]

                        # checking whether leave type list sequence and leave sequence from leave sql matches
                        if type_dict['leave_seq'] == leave_seq:
                            # updating leave type list in master data
                            type_dict['alloc_count'] = leave_alloc_count
                            type_dict['leave_remain'] = leave_alloc_count if type_dict['leave_remain'] == 0 else \
                                type_dict['leave_remain']
                            if leave_month:
                                type_dict[str(leave_month)] = leave_leave_count
                            type_dict['leave_remain'] = type_dict['leave_remain'] - leave_leave_count
                            break

        # define a fuction for key
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
            'model': "yearly.leave.summary.report.wizard",
            'form': self.read()[0],
            'csr': final_data_list,
            'leave_type_list': leave_type_list,
            'year': year,
            'work_location_name': work_location_name,
            'dept_name': dept_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data
