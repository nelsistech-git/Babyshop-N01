from odoo import fields, models, api
from calendar import monthrange
from datetime import date
import datetime
from itertools import groupby
from datetime import datetime
import xlsxwriter

import base64
from io import BytesIO


class EmployeePFDetailsReportWizard(models.TransientModel):
    _name = "employee.pf.details.report.wizard"
    _description = "Employee PF Details Report"

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

    file_data = fields.Binary('Employee PF Details Report')
    from_year = fields.Selection(get_years, string='From Year')
    to_year = fields.Selection(get_years, string='To Year')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       default=lambda self: self._get_work_loc(),
                                       domain=lambda self: self._set_domain_work_loc())
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')

    category_ids = fields.Many2many('hr.employee.category', 'employee_pf_details_employee_category_rel', 
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

    def employee_pf_details_report_excel(self):
        from_year = self.from_year
        to_year = self.to_year
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        # get data from sql
        data = self.employee_pf_details_report_sql(from_year, to_year, user_work_location_id, department_id, employee_id)

        file_name = "Employee PF Details Report.xlsx"
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

        sheet = workbook.add_worksheet('Employee PF Details Report')

        sheet.merge_range(3, 0, 3, 4, 'Work/Job Location: {0}'.format(data['work_loc_name']), format1)
        sheet.merge_range(4, 0, 4, 4, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)

        sheet.merge_range(3, 13, 3, 17, 'Year: {0}'.format(data['year'] + "-" + data['to_year']), format1)
        sheet.merge_range(4, 13, 4, 17, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)


        sheet.merge_range(0, 0, 2, 17,
                          "Employee PF Details Report",
                          format0)

        sheet.write(6, 0, 'Employee Name', format1)
        sheet.write(6, 1, 'Employee ID', format3)
        sheet.write(6, 2, 'Department', format3)
        sheet.write(6, 3, 'Designation', format3)
        sheet.write(6, 4, 'Year.', format3)
        sheet.write(6, 5, 'Jan', format2)
        sheet.write(6, 6, 'Feb', format2)
        sheet.write(6, 7, 'Mar', format2)
        sheet.write(6, 8, 'Apr', format2)
        sheet.write(6, 9, 'May.', format3)
        sheet.write(6, 10, 'Jun', format2)
        sheet.write(6, 11, 'Jul', format2)
        sheet.write(6, 12, 'Aug', format2)
        sheet.write(6, 13, 'Sep', format2)
        sheet.write(6, 14, 'Oct.', format3)
        sheet.write(6, 15, 'Nov', format2)
        sheet.write(6, 16, 'Dec', format2)
        sheet.write(6, 17, 'Total', format2)

        total_jan = 0.00
        total_feb = 0.00
        total_march = 0.00
        total_april = 0.00
        total_may = 0.00
        total_jun = 0.00
        total_jul = 0.00
        total_aug = 0.00
        total_sep = 0.00
        total_oct = 0.00
        total_nov = 0.00
        total_dec = 0.00
        total_balance = 0.00

        ro = 5
        row = 5
        col = 0

        for rec in data['csr']:
            row += 2
            sheet.merge_range(ro, 0, ro, 17, 'Branch: {0}'.format(rec['loc_name']), format1)

            for empl in rec['emp_details']:
                if 'emp_year_details' in empl:
                    row_merge = len(empl['emp_year_details']) - 1
                    sheet.write(row, col + 0, empl['employee_name'], format4)
                    sheet.write(row, col + 1, str(empl['emp_id']), format4)
                    sheet.write(row, col + 2, empl['dept_name'], format4)
                    sheet.write(row, col + 3, empl['designation'], format4)

                    for rec2 in empl['emp_year_details']:
                        total_balance += (rec2['total'])
                        total_jan = total_jan + (rec2['jn_pf_amont'])
                        total_feb = total_feb + (rec2['feb_pf_amont'])
                        total_march = total_march + (rec2['march_pf_amont'])
                        total_april = total_april + (rec2['april_pf_amont'])
                        total_may = total_may + (rec2['may_pf_amont'])
                        total_jun = total_jun + (rec2['june_pf_amont'])
                        total_jul = total_jul + (rec2['july_pf_amont'])
                        total_aug = total_aug + (rec2['august_pf_amont'])
                        total_sep = total_sep + (rec2['sept_pf_amont'])
                        total_oct = total_oct + (rec2['oct_pf_amont'])
                        total_nov = total_nov + (rec2['nov_pf_amont'])
                        total_dec = total_dec + (rec2['dec_pf_amont'])

                        sheet.write(row, col + 4, rec2['pf_year'], format6)
                        sheet.write(row, col + 5, rec2['jn_pf_amont'], format6)
                        sheet.write(row, col + 6, rec2['feb_pf_amont'], format6)
                        sheet.write(row, col + 7, rec2['march_pf_amont'], format6)
                        sheet.write(row, col + 8, rec2['april_pf_amont'], format6)
                        sheet.write(row, col + 9, rec2['may_pf_amont'], format6)
                        sheet.write(row, col + 10, rec2['june_pf_amont'], format6)
                        sheet.write(row, col + 11, rec2['july_pf_amont'], format6)
                        sheet.write(row, col + 12, rec2['august_pf_amont'], format6)
                        sheet.write(row, col + 13, rec2['sept_pf_amont'], format6)
                        sheet.write(row, col + 14, rec2['oct_pf_amont'], format6)
                        sheet.write(row, col + 15, rec2['nov_pf_amont'], format6)
                        sheet.write(row, col + 16, rec2['dec_pf_amont'], format6)
                        sheet.write(row, col + 17, '{0:,.2f}'.format(rec2['total']), format5)
                        row = row + 1
                        ro = row + 1

            final_row = row
            final_col = 0

            sheet.merge_range(final_row, final_col, final_row, final_col + 4,
                              'Total', format7)
            sheet.write(final_row, final_col + 5, '{0:,.2f}'.format(total_jan), format7)
            sheet.write(final_row, final_col + 6, '{0:,.2f}'.format(total_feb), format7)
            sheet.write(final_row, final_col + 7, '{0:,.2f}'.format(total_march), format7)
            sheet.write(final_row, final_col + 8, '{0:,.2f}'.format(total_april), format7)
            sheet.write(final_row, final_col + 9, '{0:,.2f}'.format(total_may), format7)
            sheet.write(final_row, final_col + 10, '{0:,.2f}'.format(total_jun), format7)
            sheet.write(final_row, final_col + 11, '{0:,.2f}'.format(total_jul), format7)
            sheet.write(final_row, final_col + 12, '{0:,.2f}'.format(total_aug), format7)
            sheet.write(final_row, final_col + 13, '{0:,.2f}'.format(total_sep), format7)
            sheet.write(final_row, final_col + 14, '{0:,.2f}'.format(total_oct), format7)
            sheet.write(final_row, final_col + 15, '{0:,.2f}'.format(total_nov), format7)
            sheet.write(final_row, final_col + 16, '{0:,.2f}'.format(total_dec), format7)
            sheet.write(final_row, final_col + 17, '{0:,.2f}'.format(total_balance), format7)
            # ro += 2




        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee PF Details Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.pf.details.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_pf_details_report_pdf(self):
        from_year = self.from_year
        to_year = self.to_year
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        data = self.employee_pf_details_report_sql(from_year, to_year, user_work_location_id, department_id, employee_id)
        return self.env.ref('custom_hr_report.emp_pf_details_report_tmpl').with_context(
            landscape=True).report_action(self, data=data)

    def employee_pf_details_report_sql(self, from_year, to_year, user_work_location_id, department_id, employee_id):

        work_loc_filter = ""
        dept_filter = ""
        emp_filter = ""

        work_location_name = "All"
        dept_name = "All"
        employee_name = "All"
        dept_name = "All"
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"


        if user_work_location_id:
            work_loc_filter = "AND hre.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if department_id:
            dept_filter = "AND hre.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if employee_id:
            emp_filter = "AND hre.id = %s" % employee_id.id

        loc_sql = """SELECT stl.id as loc_id, stl.name AS loc_name
                    FROM hr_employee hre
                    LEFT JOIN stock_location stl ON stl.id = hre.user_work_location_id where stl.name is not null 
                    {0} {1} {2}
                    group by stl.id,stl.name
                    """.format(work_loc_filter, emp_filter, dept_filter)
        self.env.cr.execute(loc_sql)
        loc_res = self.env.cr.dictfetchall()

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND hre.sbu_unit_id = {0}".format(self.sbu_unit_id.id) 

        # print(loc_res)
        for loc in loc_res:
            emp_sql = """SELECT hre.id as emp_id, hre.id_card_no as id_card, hre.name as employee_name, hd.name->>'en_US' AS dept_name,hj.name->>'en_US' AS designation, stl.name AS loc_name
                         FROM hr_employee hre
                         LEFT JOIN hr_department AS hd on hd.id = hre.department_id
                         LEFT JOIN hr_job hj ON hj.id = hre.job_id
                         LEFT JOIN stock_location stl ON stl.id = hre.user_work_location_id where stl.id = {0} {1} {2}
                         ORDER BY hre.id""".format(loc['loc_id'], emp_filter, dept_filter)
            self.env.cr.execute(emp_sql)
            emp_res = self.env.cr.dictfetchall()
            if emp_res:
                loc['emp_details'] = emp_res

            for rec in emp_res:
                if rec['loc_name']:
                # print(rec)
                    data_sql = ("""SELECT pf_year, jn_pf_amont,feb_pf_amont,march_pf_amont,dec_pf_amont, april_pf_amont, may_pf_amont, june_pf_amont, july_pf_amont, august_pf_amont, sept_pf_amont, 
                                    oct_pf_amont, nov_pf_amont, dec_pf_amont, employee_name, emp_id, dept_name, location_name, designation,
                                    (jn_pf_amont+feb_pf_amont+march_pf_amont+april_pf_amont+may_pf_amont+june_pf_amont+july_pf_amont+august_pf_amont+sept_pf_amont+oct_pf_amont+nov_pf_amont+dec_pf_amont) as total
                                    FROM(
                                        SELECT hrepf.year as pf_year, hre.name as employee_name, hre.id as emp_id, hd.name->>'en_US' as dept_name, sl.name AS location_name,hj.name->>'en_US' as designation,
                                        SUM(CASE WHEN hrepf.month = '01' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS jn_pf_amont,
                                        SUM(CASE WHEN hrepf.month = '02' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS feb_pf_amont,
                                        SUM(CASE WHEN hrepf.month = '03' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS march_pf_amont,
                                        SUM(CASE WHEN hrepf.month = '04' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS april_pf_amont,
                                        SUM(CASE WHEN hrepf.month = '05' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS may_pf_amont,
                                        SUM(CASE WHEN hrepf.month = '06' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS june_pf_amont,
                                        SUM(CASE WHEN hrepf.month = '07' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS july_pf_amont,
                                        SUM(CASE WHEN hrepf.month = '08' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS august_pf_amont,
                                        SUM(CASE WHEN hrepf.month = '09' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS sept_pf_amont,
                                        SUM(CASE WHEN hrepf.month = '10' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS oct_pf_amont,
                                        SUM(CASE WHEN hrepf.month = '11' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS nov_pf_amont,
                                        SUM(CASE WHEN hrepf.month = '12' THEN COALESCE(hrepf.pf_amount, 0) ELSE 0 END) AS dec_pf_amont
                                        FROM hr_employee hre
                                        JOIN hr_employee_pf hrepf ON hrepf.employee_id = hre.id
                                        --LEFT JOIN hr_contract hc ON hc.employee_id = hre.id
                                        LEFT JOIN hr_job hj ON hj.id = hre.job_id
                                        LEFT JOIN hr_department hd ON hd.id = hre.department_id
                                        LEFT JOIN stock_location sl ON sl.id = hre.user_work_location_id
                                        {8} JOIN (   
                                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                                {7}
                                                GROUP BY emp_id
                                            ) emp_tag ON emp_tag.emp_id = hre.id
                                        WHERE hrepf.year BETWEEN '{0}' AND '{1}' {2} {3} and hre.id = {4} {5} {6}
                                        --hc.state = 'open' AND hre.active = 'true' AND 
                                        GROUP BY hre.id, hrepf.year, hd.name, sl.name, hj.name
                                        order by hre.id asc
                                        ) tbl1
                                       """.format(from_year, to_year,
                                                work_loc_filter, dept_filter, 
                                                rec['emp_id'], emp_filter,
                                                business_unit_filter, tags_filter,
                                                tag_filter_join))
                    self.env.cr.execute(data_sql)
                    data_res = self.env.cr.dictfetchall()
                    if data_res:
                        rec['emp_year_details'] = data_res
        # define a fuction for key
        def key_func(k):
            if k['loc_name']:
                return k['loc_name']

        # data_res = sorted(emp_res, key=key_func)

        data_list = []

        for key, value in groupby(emp_res, key_func):
            vals = {
                key: list(value)
            }
            data_list.append(vals)

        total_jan = 0
        total_feb = 0
        total_march = 0
        total_april = 0
        total_may = 0
        total_june = 0
        total_july = 0
        total_aug = 0
        total_sep = 0
        total_oct = 0
        total_nov = 0
        total_dec = 0
        total = 0


        data = {
            'model': "employee.pf.details.report.wizard",
            'form': self.read()[0],
            'csr': loc_res,
            'year': from_year,
            'to_year': self.to_year,
            'total_january': total_jan,
            'total_february': total_feb,
            'total_march': total_march,
            'total_april': total_april,
            'total_may': total_may,
            'total_june': total_june,
            'total_july': total_july,
            'total_august': total_aug,
            'total_september': total_sep,
            'total_october': total_oct,
            'total_november': total_nov,
            'total_december': total_dec,
            'total': total,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data
