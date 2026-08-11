from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import datetime
import copy
from datetime import datetime
from itertools import groupby

import xlsxwriter

import base64
from io import BytesIO


class EmployeePFSummeryReportWizard(models.TransientModel):
    _name = "employee.pf.summery.report.wizard"
    _description = "Employee PF Summary Report"

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

    file_data = fields.Binary('Employee PF Summary Report')
    from_year = fields.Selection(get_years, string='From Year')
    to_year = fields.Selection(get_years, string='To Year')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       default=lambda self: self._get_work_loc(),
                                       domain=lambda self: self._set_domain_work_loc())
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')

    category_ids = fields.Many2many('hr.employee.category', 'employee_pf_summery_employee_category_rel', 
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

    @api.constrains('from_year', 'to_year')
    def date_constrains(self):
        if int(self.to_year) < int(self.from_year):
            raise ValidationError(_('From year cannot be less than the to year.'))

    def employee_pf_summery_report_excel(self):
        from_year = self.from_year
        to_year = self.to_year
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        # get data from sql
        data = self.employee_pf_summery_report_sql(from_year, to_year, user_work_location_id, department_id, employee_id)

        file_name = "Employee PF Summary Report ({0} - {1}).xlsx".format(from_year, to_year)
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

                sheet.write(5, 0, 'Sl. No.', format2)
                sheet.write(5, 1, 'Employee Name', format2)
                sheet.write(5, 2, 'Employee ID', format2)
                sheet.write(5, 3, 'Department', format2)
                sheet.write(5, 4, 'Designation', format2)

                year_list = data['year_list']
                head_col = 5

                for y in range(len(year_list)):
                    sheet.write(4, head_col, year_list[y]['year'], format2)
                    head_col = head_col + 1
                sheet.write(4, head_col, 'Total', format2)

                sheet.merge_range(0, 0, 0, head_col, "{0}".format(data['form']['company_id'][1]), format0)
                sheet.merge_range(1, 0, 2, head_col, "Employee PF Summary Report", format0)
                
                sheet.merge_range(3, 0, 3, int(head_col / 2), 'Work/Job Location: {0}'.format(line[line2][0]['loc_name']), format1)
                sheet.merge_range(3, int((head_col) / 2) + 1, 3, head_col, 'Year: {0} - {1}'.format(from_year, to_year), format3)

                sheet.merge_range(4, 0, 4, int(head_col / 2), 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
                sheet.merge_range(4, int((head_col) / 2) + 1, 4, head_col, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)

                    

                row = 6
                col = 0

                sl_no = 1
                total_pf_amt = 0
                t_total_pf_amt = 0

                for line3 in line[line2]:
                    sheet.write(row, col, sl_no, format5)
                    col = col + 1
                    sheet.write(row, col, line3['emp_name'], format4)
                    col = col + 1
                    sheet.write(row, col, line3['old_emp_id'], format4)
                    col = col + 1
                    sheet.write(row, col, line3['dept_name'], format4)
                    col = col + 1
                    sheet.write(row, col, line3['job_name'], format4)
                    col = col + 1
                    for j in line3['year_list']:
                        sheet.write(row, col, round(j['amt'], 2), format5)
                        total_pf_amt = total_pf_amt + j['amt']
                        col = col + 1
                    sheet.write(row, col, round(total_pf_amt, 2), format5)
                    t_total_pf_amt = t_total_pf_amt + total_pf_amt

                    row = row + 1
                    col = 0
                    sl_no = sl_no + 1
                    total_pf_amt = 0

                sheet.merge_range(row, col, row, col + 4, 'Total', format7)
                final_col = 5
                for y in range(len(year_list)):
                    sheet.write(row, final_col, round(sum(
                        year['amt'] for data in line[line2] for year in data['year_list'] if
                        year['year'] == year_list[y]['year']), 2), format2)
                    final_col = final_col + 1
                sheet.write(row, final_col, round(t_total_pf_amt, 2), format2)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee PF Summary Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.pf.summery.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_pf_summery_report_pdf(self):
        from_year = self.from_year
        to_year = self.to_year
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        data = self.employee_pf_summery_report_sql(from_year, to_year, user_work_location_id, department_id, employee_id)
        return self.env.ref('custom_hr_report.emp_pf_summery_report_tmpl').with_context(
            landscape=True).report_action(self, data=data)

    def employee_pf_summery_report_sql(self, from_year, to_year, user_work_location_id, department_id, employee_id):
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

        order_by = "main_tbl.emp_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "main_tbl.old_emp_id"
        print(order_by)

        if user_work_location_id:
            work_loc_filter = "AND hr.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if department_id:
            dept_filter = "AND hr.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if employee_id:
            emp_filter = "AND hr.id = %s" % employee_id.id

        year_list = []
        for rec in range(int(from_year), int(to_year) + 1):
            vals = {
                'year': str(rec),
                'amt': 0.00
            }
            year_list.append(vals)

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND hr.sbu_unit_id = {0}".format(self.sbu_unit_id.id)  

        # master sql - employee info
        data_sql = """
                    SELECT main_tbl.emp_id, main_tbl.emp_name, main_tbl.old_emp_id, main_tbl.user_work_location_id, sl.name AS loc_name, hd.name->>'en_US' AS dept_name,hj.name->>'en_US' AS job_name
                    FROM (
                        SELECT hr.id AS emp_id, hr.name AS emp_name, hr.id_card_no AS old_emp_id, hr.user_work_location_id AS user_work_location_id, hr.job_id AS job_id, hr.department_id AS department_id
                        FROM hr_employee hr
                        JOIN hr_contract hc ON hc.employee_id = hr.id
                        {7} JOIN (
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {6}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = hr.id
                        WHERE hc.state = 'open' AND hr.active = 'true' {2} {3} {4} {5}
                    ) main_tbl
                    LEFT JOIN hr_employee_pf hrepf ON hrepf.employee_id = main_tbl.emp_id
                    LEFT JOIN hr_job hj ON hj.id = main_tbl.job_id
                    LEFT JOIN hr_department hd ON hd.id = main_tbl.department_id
                    LEFT JOIN stock_location sl ON sl.id = main_tbl.user_work_location_id
                    WHERE hrepf.year BETWEEN '{0}' AND '{1}'
                    GROUP BY main_tbl.emp_id, main_tbl.emp_name, main_tbl.old_emp_id, main_tbl.user_work_location_id, hd.name, sl.name, hj.name
                    --  ORDER BY main_tbl.emp_id ASC
                    ORDER BY {8}
                    """.format(from_year, to_year,
                                work_loc_filter, dept_filter, 
                                emp_filter, business_unit_filter,
                                tags_filter, tag_filter_join,
                                order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        # pf amount sql
        pf_sql = """
                    SELECT main_tbl.emp_id, hrepf.year, COALESCE(SUM(hrepf.pf_amount), 0) AS pf_amount
                    FROM (
                        SELECT hr.id as emp_id
                        FROM hr_employee hr
                        JOIN hr_contract hc ON hc.employee_id = hr.id
                        WHERE hc.state = 'open' AND hr.active = 'true' {2} {3} {4}
                        GROUP BY hr.id
                        ORDER BY hr.id asc
                    ) main_tbl
                    LEFT JOIN hr_employee_pf hrepf ON hrepf.employee_id = main_tbl.emp_id
                    WHERE hrepf.year BETWEEN '{0}' and '{1}'
                    GROUP BY main_tbl.emp_id, hrepf.year
                    ORDER BY main_tbl.emp_id, hrepf.year
                    """.format(from_year, to_year, work_loc_filter, dept_filter, emp_filter)
        self.env.cr.execute(pf_sql)
        pf_data_res = self.env.cr.dictfetchall()
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
                'year_list': copy.deepcopy(year_list)
            }
            data_list.append(vals)

        # updating leave info
        for rec in data_list:  # master data loop
            emp_id = rec['emp_id']
            year_list = rec['year_list']
            for rec2 in pf_data_res:  # pf data loop
                pf_emp_id = rec2['emp_id']
                pf_year = rec2['year']
                pf_amt = rec2['pf_amount']
                # checking whether leave employee id and master data employee id matches
                if pf_emp_id == emp_id:
                    for j in range(len(year_list)):  # year list loop
                        year_dict = year_list[j]
                        # checking whether year list year and year from pf sql matches
                        if year_dict['year'] == pf_year:
                            # updating year list in master data
                            year_dict['amt'] = pf_amt
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
            'model': "employee.pf.details.report.wizard",
            'form': self.read()[0],
            'csr': final_data_list,
            'year_list': year_list,
            'from_year': from_year,
            'to_year': to_year,
            'work_loc_name': work_location_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data
