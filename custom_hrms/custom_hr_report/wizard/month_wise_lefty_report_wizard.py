from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from calendar import monthrange
from datetime import date
import datetime
from datetime import datetime

import xlsxwriter

import base64
from io import BytesIO


class MonthWiseLeftyReportWizard(models.TransientModel):
    _name = "month.wise.lefty.report.wizard"
    _description = "Month Wise Lefty Report Wizard"

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

    file_data = fields.Binary('Month wise Lefty Report Wizard')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
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
    lefty_days = fields.Integer(string='Lefty Days', default=10)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    category_ids = fields.Many2many('hr.employee.category', 'month_wise_lefty_employee_category_rel', 
                'selected_id', 'category_id', string='Tags')

    sbu_unit_id = fields.Many2one('hr.sbu.unit', string='Office/Business Unit')


    def month_wise_lefty_report_pdf(self):
        year = self.year
        month = self.month
        lefty_days = self.lefty_days

        # get data from sql
        data = self.month_wise_lefty_report_sql(year, month, lefty_days)

        return self.env.ref(
            'custom_hr_report.month_wise_lefty_report_tmpl').with_context(landscape=True).report_action(self, data=data)

    def month_wise_lefty_report_excel(self):
        year = self.year
        month = self.month
        lefty_days = self.lefty_days

        # get data from sql
        data = self.month_wise_lefty_report_sql(year, month, lefty_days)

        file_name = "Month wise Lefty Report.xlsx"
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

        #Filter Formatting
        format10 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format10.set_align('left')
        format10.set_border()

        sheet = workbook.add_worksheet('Month wise Lefty Report')

        sheet.merge_range(0, 0, 0, 6, "{0}".format(data['form']['company_id'][1]), format0)
        sheet.merge_range(1, 0, 2, 6,
                          "Month wise Lefty Report (%s - %s)" % (data['month'], data['year']), format0)
        sheet.merge_range(3, 0, 3, 2, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format10)
        sheet.merge_range(3, 3, 3, 6, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format10)

        sheet.write(4, 0, 'Employee ID', format2)
        sheet.write(4, 1, 'Employee Name', format1)
        sheet.write(4, 2, 'Department', format1)
        sheet.write(4, 3, 'Designation', format1)
        sheet.write(4, 4, 'Last Present Date', format2)
        sheet.write(4, 5, 'Total Absent Day', format2)
        sheet.write(4, 6, 'Total Present Day', format2)



        row = 5
        col = 0

        for rec in data['csr']:
            sheet.write(row, col, rec['emp_id_card'], format5)
            sheet.write(row, col + 1, rec['emp_name'], format4)
            sheet.write(row, col + 2, rec['dept_name'], format4)
            sheet.write(row, col + 3, rec['des_name'], format4)
            sheet.write(row, col + 4, datetime.strptime(str(rec['last_present_day']), '%Y-%m-%d').strftime('%d-%b-%Y') if rec['last_present_day'] else '', format5)
            sheet.write(row, col + 5, rec['absent_day'], format5)
            sheet.write(row, col + 6, rec['present_day'], format5)

            row = row + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Month wise Lefty Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=month.wise.lefty.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def month_wise_lefty_report_sql(self, year, month, lefty_days):
        m = int(month)
        y = int(year)
        ndays = monthrange(y, m)[1]
        start_date = date(y, m, 1)
        end_date = date(y, m, ndays)

        data_sql = """
                    SELECT employee_id, dayno
                    FROM(
                        SELECT ats.employee_id, EXTRACT(DAY FROM atsl.date) AS dayno
                        FROM attendance_sheet ats
                        JOIN attendance_sheet_line atsl ON atsl.att_sheet_id = ats.id
                        WHERE ats.state = 'done' AND atsl.status IN ('ab', 'weekend', 'ph', 'leave')
                            AND atsl.date BETWEEN '{0}' AND '{1}'
                        ORDER BY ats.employee_id, EXTRACT(DAY FROM atsl.date)
                        ) tbl1
                    WHERE tbl1.employee_id IN (
                        SELECT employee_id FROM(
                            SELECT ats.employee_id AS employee_id, COUNT(ats.id) AS empcount
                            FROM attendance_sheet ats
                            JOIN attendance_sheet_line atsl ON atsl.att_sheet_id = ats.id
                            WHERE ats.state = 'done' AND atsl.status IN ('ab', 'weekend', 'ph', 'leave')
                            and atsl.date BETWEEN '{0}' AND '{1}'
                            GROUP BY ats.employee_id
                            ORDER BY ats.employee_id
                        ) tbl2 WHERE empcount >= {2}
                    )
                    ORDER BY employee_id
                    """.format(start_date, end_date, lefty_days)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        emp_list = []
        count = 0
        prev_emp_id = 0
        prev_dayno = 0
        for rec in data_res:
            if prev_emp_id != rec['employee_id']:
                prev_emp_id = rec['employee_id']
                prev_dayno = rec['dayno']
                count = count + 1
            elif prev_emp_id == rec['employee_id']:
                if prev_dayno + 1 == rec['dayno']:
                    prev_dayno = rec['dayno']
                    count = count + 1
                    if count == lefty_days:
                        count = 0
                        prev_emp_id = 0
                        emp_list.append(rec['employee_id'])
                else:
                    count = 1
                    prev_dayno = rec['dayno']
            else:
                break

        emp_filter = ""
        emp_filter2 = ""
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "tbl1.emp_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "tbl1.emp_id_card"
        # print(order_by)

        emp_tuple = tuple(set(emp_list))

        if len(emp_tuple) > 1:
            emp_filter = "AND he.id IN {0}".format(emp_tuple)
            emp_filter2 = "AND ats.employee_id IN {0}".format(emp_tuple)
        elif len(emp_tuple) == 1:
            emp_filter = "AND he.id = {0}".format(emp_tuple[0])
            emp_filter2 = "AND ats.employee_id = {0}".format(emp_tuple[0])
        else:
            pass

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])     
                                
        if self.sbu_unit_id:
            business_unit_filter = "AND he.sbu_unit_id = {0}".format(self.sbu_unit_id.id)

        main_sql = """
                    SELECT tbl1.emp_name, tbl1.dept_name, tbl1.des_name, tbl1.emp_id_card, DATE(tbl2.last_present_day) AS last_present_day, tbl1.absent_day, tbl1.present_day
                    FROM(
                        SELECT he.id AS emp_id, he.name AS emp_name, hd.name->>'en_US' AS dept_name,hj.name->>'en_US' AS des_name,
                        he.id_card_no AS emp_id_card, ats.no_absence AS absent_day, ats.no_presence AS present_day
                        FROM attendance_sheet ats
                        JOIN hr_employee he ON he.id = ats.employee_id
                        LEFT JOIN hr_job hj ON hj.id = he.job_id
                        LEFT JOIN hr_department hd ON hd.id = he.department_id
                        {4} JOIN (
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {3}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = he.id
                        WHERE ats.state = 'done' {0} {2}
                        GROUP BY he.id, he.name, hd.name, hj.name, he.id_card_no, ats.no_absence, ats.no_presence
                        ORDER BY he.id
                    ) tbl1
                    LEFT JOIN (
                        SELECT DISTINCT ON (ats.employee_id) employee_id, MAX(atsl.date) AS last_present_day
                        FROM attendance_sheet ats
                        JOIN attendance_sheet_line atsl ON atsl.att_sheet_id = ats.id
                        WHERE ats.state = 'done' AND atsl.status IS NULL {1}
                        GROUP BY ats.employee_id
                        ORDER BY ats.employee_id ASC
                    ) tbl2 ON tbl2.employee_id = tbl1.emp_id
                    GROUP BY tbl1.emp_name, tbl1.dept_name, tbl1.des_name, tbl1.emp_id_card, tbl2.last_present_day, tbl1.present_day, tbl1.absent_day
                    -- ORDER BY tbl1.emp_id_card, tbl1.emp_name
                    ORDER BY {5}
                    """.format(emp_filter, emp_filter2, 
                                business_unit_filter, tags_filter,
                                tag_filter_join, order_by)
        self.env.cr.execute(main_sql)
        main_data = self.env.cr.dictfetchall()

        data = {
            'model': "month.wise.lefty.report.wizard",
            'form': self.read()[0],
            'csr': main_data,
            'month': dict(self._fields['month'].selection).get(self.month),
            'year': year,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data
