from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import datetime
from datetime import datetime
import copy
from itertools import groupby
import xlsxwriter

import base64
from io import BytesIO


class EmployeePFReportWizard(models.TransientModel):
    _name = "employee.pf.report.wizard"
    _description = "Employee PF Report Wizard"

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

    file_data = fields.Binary('Employee PF Report Wizard')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', default=lambda self: self._get_work_loc(), domain=lambda self: self._set_domain_work_loc())
    department_id = fields.Many2one('hr.department', string='Department')
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

    category_ids = fields.Many2many('hr.employee.category', 'employee_pf_employee_category_rel', 
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

    def employee_pf_report_pdf(self):
        year = self.year
        month = self.month
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        # get data from sql
        data = self.employee_pf_report_sql(year, month, user_work_location_id, department_id, employee_id)

        return self.env.ref(
            'custom_hr_report.employee_pf_report_tmpl').with_context(landscape=True).report_action(self, data=data)

    def employee_pf_report_excel(self):
        year = self.year
        month = self.month
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        # get data from sql
        data = self.employee_pf_report_sql(year, month, user_work_location_id, department_id, employee_id)

        file_name = "Employee PF Report.xlsx"
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

                sl_no = 1
                total_pf_amt = 0
                grand_jan_pf_amt = 0
                grand_feb_pf_amt = 0
                grand_mar_pf_amt = 0
                grand_apr_pf_amt = 0
                grand_may_pf_amt = 0
                grand_jun_pf_amt = 0
                grand_jul_pf_amt = 0
                grand_aug_pf_amt = 0
                grand_sep_pf_amt = 0
                grand_oct_pf_amt = 0
                grand_nov_pf_amt = 0
                grand_dec_pf_amt = 0
                grand_total_pf_amt = 0

                head_row = 5
                head_col = 0

                sheet.write(head_row, head_col, 'Sl. No.', format2)
                head_col = head_col + 1
                sheet.write(head_row, head_col, 'Employee Name', format1)
                head_col = head_col + 1
                sheet.write(head_row, head_col, 'Employee ID', format1)
                head_col = head_col + 1
                sheet.write(head_row, head_col, 'Work/Job Location', format1)
                head_col = head_col + 1
                sheet.write(head_row, head_col, 'Department', format1)
                head_col = head_col + 1
                sheet.write(head_row, head_col, 'Designation', format1)
                head_col = head_col + 1

                if not data['form']['month']:
                    sheet.write(head_row, head_col, 'Jan', format2)
                    head_col = head_col + 1
                    sheet.write(head_row, head_col, 'Feb', format2)
                    head_col = head_col + 1
                    sheet.write(head_row, head_col, 'Mar', format2)
                    head_col = head_col + 1
                    sheet.write(head_row, head_col, 'Apr', format2)
                    head_col = head_col + 1
                    sheet.write(head_row, head_col, 'May', format2)
                    head_col = head_col + 1
                    sheet.write(head_row, head_col, 'Jun', format2)
                    head_col = head_col + 1
                    sheet.write(head_row, head_col, 'Jul', format2)
                    head_col = head_col + 1
                    sheet.write(head_row, head_col, 'Aug', format2)
                    head_col = head_col + 1
                    sheet.write(head_row, head_col, 'Sep', format2)
                    head_col = head_col + 1
                    sheet.write(head_row, head_col, 'Oct', format2)
                    head_col = head_col + 1
                    sheet.write(head_row, head_col, 'Nov', format2)
                    head_col = head_col + 1
                    sheet.write(head_row, head_col, 'Dec', format2)
                    head_col = head_col + 1
                else:
                    if data['form']['month'] == '01':
                        sheet.write(head_row, head_col, 'Jan', format2)
                    elif data['form']['month'] == '02':
                        sheet.write(head_row, head_col, 'Feb', format2)
                    elif data['form']['month'] == '03':
                        sheet.write(head_row, head_col, 'Mar', format2)
                    elif data['form']['month'] == '04':
                        sheet.write(head_row, head_col, 'Apr', format2)
                    elif data['form']['month'] == '05':
                        sheet.write(head_row, head_col, 'May', format2)
                    elif data['form']['month'] == '06':
                        sheet.write(head_row, head_col, 'Jun', format2)
                    elif data['form']['month'] == '07':
                        sheet.write(head_row, head_col, 'Jul', format2)
                    elif data['form']['month'] == '08':
                        sheet.write(head_row, head_col, 'Aug', format2)
                    elif data['form']['month'] == '09':
                        sheet.write(head_row, head_col, 'Sep', format2)
                    elif data['form']['month'] == '10':
                        sheet.write(head_row, head_col, 'Oct', format2)
                    elif data['form']['month'] == '11':
                        sheet.write(head_row, head_col, 'Nov', format2)
                    else:
                        sheet.write(head_row, head_col, 'Dec', format2)
                    head_col = head_col + 1

                sheet.write(head_row, head_col, 'Total', format2)
                head_col = head_col + 1
                sheet.write(head_row, head_col, 'Remarks', format2)

                row = 6
                col = 0

                for line3 in line[line2]:
                    sheet.write(row, col, sl_no, format5)
                    col = col + 1
                    sheet.write(row, col, line3['emp_name'], format4)
                    col = col + 1
                    sheet.write(row, col, line3['old_emp_id'], format4)
                    col = col + 1
                    sheet.write(row, col, line3['loc_name'], format4)
                    col = col + 1
                    sheet.write(row, col, line3['dept_name'], format4)
                    col = col + 1
                    sheet.write(row, col, line3['job_name'], format4)
                    col = col + 1

                    if not data['form']['month']:
                        for line4 in line3['month_list']:
                            sheet.write(row, col, round(line4['01'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['01']
                            grand_jan_pf_amt = grand_jan_pf_amt + line4['01']
                            grand_total_pf_amt = grand_total_pf_amt + line4['01']
                            col = col + 1
                            sheet.write(row, col, round(line4['02'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['02']
                            grand_feb_pf_amt = grand_feb_pf_amt + line4['02']
                            grand_total_pf_amt = grand_total_pf_amt + line4['02']
                            col = col + 1
                            sheet.write(row, col, round(line4['03'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['03']
                            grand_mar_pf_amt = grand_mar_pf_amt + line4['03']
                            grand_total_pf_amt = grand_total_pf_amt + line4['03']
                            col = col + 1
                            sheet.write(row, col, round(line4['04'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['04']
                            grand_apr_pf_amt = grand_apr_pf_amt + line4['04']
                            grand_total_pf_amt = grand_total_pf_amt + line4['04']
                            col = col + 1
                            sheet.write(row, col, round(line4['05'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['05']
                            grand_may_pf_amt = grand_may_pf_amt + line4['05']
                            grand_total_pf_amt = grand_total_pf_amt + line4['05']
                            col = col + 1
                            sheet.write(row, col, round(line4['06'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['06']
                            grand_jun_pf_amt = grand_jun_pf_amt + line4['06']
                            grand_total_pf_amt = grand_total_pf_amt + line4['06']
                            col = col + 1
                            sheet.write(row, col, round(line4['07'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['07']
                            grand_jul_pf_amt = grand_jul_pf_amt + line4['07']
                            grand_total_pf_amt = grand_total_pf_amt + line4['07']
                            col = col + 1
                            sheet.write(row, col, round(line4['08'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['08']
                            grand_aug_pf_amt = grand_aug_pf_amt + line4['08']
                            grand_total_pf_amt = grand_total_pf_amt + line4['08']
                            col = col + 1
                            sheet.write(row, col, round(line4['09'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['09']
                            grand_sep_pf_amt = grand_sep_pf_amt + line4['09']
                            grand_total_pf_amt = grand_total_pf_amt + line4['09']
                            col = col + 1
                            sheet.write(row, col, round(line4['10'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['10']
                            grand_oct_pf_amt = grand_oct_pf_amt + line4['10']
                            grand_total_pf_amt = grand_total_pf_amt + line4['10']
                            col = col + 1
                            sheet.write(row, col, round(line4['11'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['11']
                            grand_nov_pf_amt = grand_nov_pf_amt + line4['11']
                            grand_total_pf_amt = grand_total_pf_amt + line4['11']
                            col = col + 1
                            sheet.write(row, col, round(line4['12'], 2), format6)
                            total_pf_amt = total_pf_amt + line4['12']
                            grand_dec_pf_amt = grand_dec_pf_amt + line4['12']
                            grand_total_pf_amt = grand_total_pf_amt + line4['12']
                            col = col + 1
                    else:
                        for line4 in line3['month_list']:
                            if data['form']['month'] == '01':
                                sheet.write(row, col, round(line4['01'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['01']
                                grand_jan_pf_amt = grand_jan_pf_amt + line4['01']
                                grand_total_pf_amt = grand_total_pf_amt + line4['01']
                            elif data['form']['month'] == '02':
                                sheet.write(row, col, round(line4['02'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['02']
                                grand_feb_pf_amt = grand_feb_pf_amt + line4['02']
                                grand_total_pf_amt = grand_total_pf_amt + line4['02']
                            elif data['form']['month'] == '03':
                                sheet.write(row, col, round(line4['03'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['03']
                                grand_mar_pf_amt = grand_mar_pf_amt + line4['03']
                                grand_total_pf_amt = grand_total_pf_amt + line4['03']
                            elif data['form']['month'] == '04':
                                sheet.write(row, col, round(line4['04'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['04']
                                grand_apr_pf_amt = grand_apr_pf_amt + line4['04']
                                grand_total_pf_amt = grand_total_pf_amt + line4['04']
                            elif data['form']['month'] == '05':
                                sheet.write(row, col, round(line4['05'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['05']
                                grand_may_pf_amt = grand_may_pf_amt + line4['05']
                                grand_total_pf_amt = grand_total_pf_amt + line4['05']
                            elif data['form']['month'] == '06':
                                sheet.write(row, col, round(line4['06'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['06']
                                grand_jun_pf_amt = grand_jun_pf_amt + line4['06']
                                grand_total_pf_amt = grand_total_pf_amt + line4['06']
                            elif data['form']['month'] == '07':
                                sheet.write(row, col, round(line4['07'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['07']
                                grand_jul_pf_amt = grand_jul_pf_amt + line4['07']
                                grand_total_pf_amt = grand_total_pf_amt + line4['07']
                            elif data['form']['month'] == '08':
                                sheet.write(row, col, round(line4['08'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['08']
                                grand_aug_pf_amt = grand_aug_pf_amt + line4['08']
                                grand_total_pf_amt = grand_total_pf_amt + line4['08']
                            elif data['form']['month'] == '09':
                                sheet.write(row, col, round(line4['09'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['09']
                                grand_sep_pf_amt = grand_sep_pf_amt + line4['09']
                                grand_total_pf_amt = grand_total_pf_amt + line4['09']
                            elif data['form']['month'] == '10':
                                sheet.write(row, col, round(line4['10'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['10']
                                grand_oct_pf_amt = grand_oct_pf_amt + line4['10']
                                grand_total_pf_amt = grand_total_pf_amt + line4['10']
                            elif data['form']['month'] == '11':
                                sheet.write(row, col, round(line4['11'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['11']
                                grand_nov_pf_amt = grand_nov_pf_amt + line4['11']
                                grand_total_pf_amt = grand_total_pf_amt + line4['11']
                            else:
                                sheet.write(row, col, round(line4['12'], 2), format6)
                                total_pf_amt = total_pf_amt + line4['12']
                                grand_dec_pf_amt = grand_dec_pf_amt + line4['12']
                                grand_total_pf_amt = grand_total_pf_amt + line4['12']
                            col = col + 1
                            break

                    sheet.write(row, col, round(total_pf_amt, 2), format6)
                    col = col + 1
                    sheet.write(row, col, None, format6)

                    row = row + 1
                    col = 0
                    sl_no = sl_no + 1
                    total_pf_amt = 0

                final_row = row
                final_col = 0

                sheet.merge_range(final_row, final_col, final_row, final_col + 5, 'Total', format3)
                final_col = final_col + 6
                if not data['form']['month']:
                    sheet.write(final_row, final_col, grand_jan_pf_amt, format6)
                    final_col = final_col + 1
                    sheet.write(final_row, final_col, round(grand_feb_pf_amt,2), format6)
                    final_col = final_col + 1
                    sheet.write(final_row, final_col, round(grand_mar_pf_amt, 2), format6)
                    final_col = final_col + 1
                    sheet.write(final_row, final_col, round(grand_apr_pf_amt, 2), format6)
                    final_col = final_col + 1
                    sheet.write(final_row, final_col, round(grand_may_pf_amt, 2), format6)
                    final_col = final_col + 1
                    sheet.write(final_row, final_col, round(grand_jun_pf_amt, 2), format6)
                    final_col = final_col + 1
                    sheet.write(final_row, final_col, round(grand_jul_pf_amt, 2), format6)
                    final_col = final_col + 1
                    sheet.write(final_row, final_col, round(grand_aug_pf_amt, 2), format6)
                    final_col = final_col + 1
                    sheet.write(final_row, final_col, round(grand_sep_pf_amt, 2), format6)
                    final_col = final_col + 1
                    sheet.write(final_row, final_col, round(grand_oct_pf_amt, 2), format6)
                    final_col = final_col + 1
                    sheet.write(final_row, final_col, round(grand_nov_pf_amt, 2), format6)
                    final_col = final_col + 1
                    sheet.write(final_row, final_col, round(grand_dec_pf_amt, 2), format6)
                    final_col = final_col + 1
                else:
                    if data['form']['month'] == '01':
                        sheet.write(row, col, round(grand_jan_pf_amt, 2), format6)
                    elif data['form']['month'] == '02':
                        sheet.write(row, col, round(grand_feb_pf_amt, 2), format6)
                    elif data['form']['month'] == '03':
                        sheet.write(row, col, round(grand_mar_pf_amt, 2), format6)
                    elif data['form']['month'] == '04':
                        sheet.write(row, col, round(grand_apr_pf_amt, 2), format6)
                    elif data['form']['month'] == '05':
                        sheet.write(row, col, round(grand_may_pf_amt, 2), format6)
                    elif data['form']['month'] == '06':
                        sheet.write(row, col, round(grand_jun_pf_amt, 2), format6)
                    elif data['form']['month'] == '07':
                        sheet.write(row, col, round(grand_jul_pf_amt, 2), format6)
                    elif data['form']['month'] == '08':
                        sheet.write(row, col, round(grand_aug_pf_amt, 2), format6)
                    elif data['form']['month'] == '09':
                        sheet.write(row, col, round(grand_sep_pf_amt, 2), format6)
                    elif data['form']['month'] == '10':
                        sheet.write(row, col, round(grand_oct_pf_amt, 2), format6)
                    elif data['form']['month'] == '11':
                        sheet.write(row, col, round(grand_nov_pf_amt, 2), format6)
                    else:
                        sheet.write(row, col, round(grand_dec_pf_amt, 2), format6)
                    final_col = final_col + 1

                sheet.write(final_row, final_col, round(grand_total_pf_amt, 2), format6)
                final_col = final_col + 1
                sheet.write(final_row, final_col, None, format6)

                sheet.merge_range(0, 0, 0, final_col, data['form']['company_id'][1], format0)
                sheet.merge_range(1, 0, 2, final_col, "Employee PF Report", format0)

                sheet.merge_range(3, 0, 3, int((final_col/2)), 'Branch: {0}'.format(line[line2][0]['loc_name']), format1)
                sheet.merge_range(4, 0, 4, int((final_col/2)), 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
                            
                sheet.merge_range(3, int((final_col/2) + 1), 3, final_col, 'Year: {0}'.format(data['form']['year']), format3)
                sheet.merge_range(4, int((final_col/2) + 1), 4, final_col, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format3)

        
        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee PF Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.pf.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_pf_report_sql(self, year, month, user_work_location_id, department_id, employee_id):
        work_loc_filter = ""
        dept_filter = ""
        emp_filter = ""
        month_filter = ""
        work_location_name = "All"
        dept_name = "All"
        filter = ""
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "emp_tbl.emp_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "emp_tbl.old_emp_id"
        print(order_by)


        if user_work_location_id:
            work_loc_filter = "AND emp_tbl.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if department_id:
            dept_filter = "AND hd.id = %s" % department_id.id
            dept_name = department_id.display_name

        if employee_id:
            emp_filter = "AND emp_tbl.emp_id = %s" % employee_id.id

        if month:
            month_filter = "AND hrpf.month = '%s'" % month

        month_list = [{
            '01': 0,
            '02': 0,
            '03': 0,
            '04': 0,
            '05': 0,
            '06': 0,
            '07': 0,
            '08': 0,
            '09': 0,
            '10': 0,
            '11': 0,
            '12': 0,
        }]

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND hre.sbu_unit_id = {0}".format(self.sbu_unit_id.id)  

        # master sql - employee info
        data_sql = """
                    SELECT emp_tbl.emp_id, emp_tbl.emp_name, emp_tbl.old_emp_id, hd.name->>'en_US' AS dept_name,hj.name->>'en_US' AS job_name, stl.name AS loc_name, COALESCE(emp_tbl.user_work_location_id, 10000) AS user_work_location_id
                    FROM (
                        SELECT hre.id AS emp_id, hre.name AS emp_name, hre.id_card_no AS old_emp_id, hre.department_id, hre.user_work_location_id, hre.job_id
                        FROM hr_employee hre
                        JOIN hr_contract hc ON hc.employee_id = hre.id
                        {7} JOIN (
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {6}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = hre.id
                        WHERE hc.state='open' {5}
                    ) emp_tbl
                    LEFT JOIN hr_department AS hd on hd.id = emp_tbl.department_id
                    LEFT JOIN hr_job hj ON hj.id = emp_tbl.job_id
                    LEFT JOIN stock_location stl ON stl.id = emp_tbl.user_work_location_id
                    WHERE emp_tbl.emp_id IN (
                        SELECT hrpf.employee_id AS emp_id
                        FROM hr_employee_pf hrpf
                        WHERE hrpf.year='{0}' {1} AND hrpf.pf_amount > 0
                        GROUP BY hrpf.employee_id, hrpf.pf_amount, hrpf.year, hrpf.month
                        ORDER BY hrpf.employee_id
                    ) {2} {3} {4}
                    -- ORDER BY emp_tbl.old_emp_id
                    ORDER BY {8}
                    """.format(year, month_filter,
                                work_loc_filter, dept_filter,
                                emp_filter, business_unit_filter,
                                tags_filter, tag_filter_join,
                                order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        pf_sql = """
                    SELECT hrpf.employee_id AS emp_id, hrpf.year, hrpf.month, COALESCE(SUM(hrpf.pf_amount), 0) AS pf_amt
                    FROM hr_employee_pf hrpf
                    WHERE hrpf.year = '{0}' {1}
                    GROUP BY hrpf.employee_id, hrpf.year, hrpf.month
                    ORDER BY hrpf.employee_id, hrpf.year, hrpf.month
                    """.format(year, month_filter)
        self.env.cr.execute(pf_sql)
        pf_res = self.env.cr.dictfetchall()

        data_list = []

        # master data - master sql data and leave type list merge
        for rec in data_res:
            vals = {
                'emp_id': rec['emp_id'],
                'user_work_location_id': rec['user_work_location_id'],
                'emp_name': rec['emp_name'],
                'old_emp_id': rec['old_emp_id'],
                'loc_name': rec['loc_name'],
                'dept_name': rec['dept_name'],
                'job_name': rec['job_name'],
                'month_list': copy.deepcopy(month_list)
            }
            data_list.append(vals)

        # updating leave info
        for rec in data_list:       # master data loop
            emp_id = rec['emp_id']
            month_list = rec['month_list']
            month_dict = month_list[0]
            for rec2 in pf_res:      # pf data loop
                pf_emp_id = rec2['emp_id']
                month = rec2['month']
                pf_amt = rec2['pf_amt']
                # checking whether pf employee id and master data employee id matches
                if pf_emp_id == emp_id:
                    for j in range(1, len(month_dict) + 1):      # month list loop

                        # checking whether month list sequence and month from pf sql matches
                        if str(j).zfill(2) == month:
                            # updating month list in master data
                            month_dict[str(j).zfill(2)] = pf_amt
                            break

        # define a fuction for key
        def key_func(k):
            return k['user_work_location_id']

        data_list = sorted(data_list, key=key_func)

        data_final_list = []

        for key, value in groupby(data_list, key_func):
            vals = {
                key: list(value)
            }
            data_final_list.append(vals)

        data = {
            'model': "employee.pf.report.wizard",
            'form': self.read()[0],
            'csr': data_final_list,
            'month_list': month_list,
            'work_location_name': work_location_name,
            'dept_name': dept_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data