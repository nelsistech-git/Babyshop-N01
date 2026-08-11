from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import xlsxwriter

import base64
from io import BytesIO


class EmployeeOvertimeReportWizard(models.TransientModel):
    _name = "employee.overtime.report.wizard"
    _description = "Employee Overtime Report Wizard"

    file_data = fields.Binary('Employee Overtime Report Wizard')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    status = fields.Many2one('hr.employee.type',string="Status")

    category_ids = fields.Many2many('hr.employee.category', 'employee_overtime_employee_category_rel', 
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

    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                        default=lambda self: self._get_work_loc(), domain=_set_domain_work_loc)


    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('Start date cannot be greater than the end date.'))

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

    def employee_overtime_report_pdf(self):
        start_date = self.start_date
        end_date = self.end_date
        employee_id = self.employee_id
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id
        status = self.status

        # get data from sql
        data = self.employee_overtime_report_sql(start_date, end_date, employee_id, department_id, user_work_location_id,status)

        return self.env.ref(
            'custom_hr_report.employee_overtime_report_id_tmpl').with_context(landscape=False).report_action(self,
                                                                                                            data=data)

    def employee_overtime_report_excel(self):
        start_date = self.start_date
        end_date = self.end_date
        employee_id = self.employee_id
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id
        status = self.status

        # get data from sql
        data = self.employee_overtime_report_sql(start_date, end_date, employee_id, department_id, user_work_location_id,status)

        file_name = "Employee Overtime Report.xlsx"
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

        sheet = workbook.add_worksheet('Employee Overtime Report')

        start_date = datetime.strptime(str(data['form']['start_date']), '%Y-%m-%d').strftime('%d-%b-%Y')
        end_date = datetime.strptime(str(data['form']['end_date']), '%Y-%m-%d').strftime('%d-%b-%Y')

        if not data['form']['employee_id']:
            sheet.merge_range(0, 0, 2, 5, "Employee Overtime Report", format0)

            sheet.merge_range(3, 0, 3, 2, 'From Date: {0}'.format(start_date), format1)
            sheet.merge_range(4, 0, 4, 2, 'To Date: {0}'.format(end_date), format1)
            sheet.merge_range(5, 0, 5, 2, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
            sheet.merge_range(6, 0, 6, 2, None, format1)


            sheet.merge_range(3, 3, 3, 5, 'Work/Job Location: {0}'.format(data['work_loc_name']), format1)
            sheet.merge_range(4, 3, 4, 5, 'Department: {0}'.format(data['dept_name']), format1)
            sheet.merge_range(5, 3, 5, 5, 'Employee Name: {0}'.format(data['employee_name']), format1)
            sheet.merge_range(6, 3, 6, 5, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)

            sheet.write(7, 0, 'Sl.', format5)
            sheet.write(7, 1, 'Date', format1)
            sheet.write(7, 2, 'Employee Name', format1)
            sheet.write(7, 3, 'Check In', format1)
            sheet.write(7, 4, 'Check Out', format1)
            sheet.write(7, 5, 'Overtime Hours', format1)

            row = 8
            col = 0
            sl_no = 1

            for rec in data['csr']:
                sheet.write(row, col, sl_no, format4)
                col = col + 1
                att_date = datetime.strptime(str(rec['attendance_date']), '%Y-%m-%d').strftime('%d-%b-%Y')
                sheet.write(row, col, att_date, format4)
                col = col + 1
                sheet.write(row, col, rec['employee_name'], format4)
                col = col + 1
                check_in_time = str(
                    timedelta(hours=int(rec['check_in_time']), minutes=(rec['check_in_time'] * 60) % 60, seconds=00))
                sheet.write(row, col, check_in_time, format4)
                col = col + 1
                check_out_time = str(
                    timedelta(hours=int(rec['check_out_time']), minutes=(rec['check_out_time'] * 60) % 60, seconds=00))
                sheet.write(row, col, check_out_time, format4)
                col = col + 1
                overtime_hours_time = str(
                    timedelta(hours=int(rec['overtime_hours_time']), minutes=(rec['overtime_hours_time'] * 60) % 60,
                              seconds=00))
                sheet.write(row, col, overtime_hours_time, format4)

                row = row + 1
                col = 0
                sl_no = sl_no + 1

        else:
            sheet.merge_range(0, 0, 2, 4, "Employee Overtime Report", format0)

            sheet.merge_range(3, 0, 3, 2, 'From Date: {0}'.format(start_date), format1)
            sheet.merge_range(4, 0, 4, 2, 'To Date: {0}'.format(end_date), format1)
            sheet.merge_range(5, 0, 5, 2, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
            sheet.merge_range(6, 0, 6, 2, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)


            sheet.merge_range(3, 3, 3, 4, 'Work/Job Location: {0}'.format(data['work_loc_name']), format1)
            sheet.merge_range(4, 3, 4, 4, 'Department: {0}'.format(data['dept_name']), format1)
            sheet.merge_range(5, 3, 5, 4, 'Employee Name: {0}'.format(data['employee_name']), format1)
            sheet.merge_range(6, 3, 6, 4, 'Employee ID: {0}'.format(data['employee_id_card']), format1)


            sheet.write(7, 0, 'Sl.', format2)
            sheet.write(7, 1, 'Date', format1)
            sheet.write(7, 2, 'Check In', format1)
            sheet.write(7, 3, 'Check Out', format1)
            sheet.write(7, 4, 'Overtime Hours', format1)

            row = 8
            col = 0
            sl_no = 1

            for rec in data['csr']:
                sheet.write(row, col, sl_no, format5)
                col = col + 1
                att_date = datetime.strptime(str(rec['attendance_date']), '%Y-%m-%d').strftime('%d-%b-%Y')
                sheet.write(row, col, att_date, format4)
                col = col + 1
                check_in_time = str(
                    timedelta(hours=int(rec['check_in_time']), minutes=(rec['check_in_time'] * 60) % 60, seconds=00))
                sheet.write(row, col, check_in_time, format4)
                col = col + 1
                check_out_time = str(
                    timedelta(hours=int(rec['check_out_time']), minutes=(rec['check_out_time'] * 60) % 60, seconds=00))
                sheet.write(row, col, check_out_time, format4)
                col = col + 1
                overtime_hours_time = str(
                    timedelta(hours=int(rec['overtime_hours_time']), minutes=(rec['overtime_hours_time'] * 60) % 60,
                              seconds=00))
                sheet.write(row, col, overtime_hours_time, format4)

                row = row + 1
                col = 0
                sl_no = sl_no + 1



        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Overtime Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.overtime.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_overtime_report_sql(self, start_date, end_date, employee_id, department_id, user_work_location_id,status):
        emp_filter = ""
        dept_filter = ""
        work_loc_filter = ""
        status_filter = ""
        dept_name = "All"
        work_location_name = "All"
        employee_name = "All"
        employee_id_card = ""
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "hre.name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "hre.id_card_no"
        print(order_by)

        if department_id:
            dept_filter = "AND hre.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            work_loc_filter = "AND sl.id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if employee_id:
            emp_filter = "AND hre.id = %s" % employee_id.id
            employee_name = employee_id.name
            employee_id_card = employee_id.id_card_no

        if status:
            status_filter = "AND hret.id = %s" % status.id
            status_name = status.name
            # employee_id_card = employee_id.id_card_no

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 
            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0]) 
                                        
                                        
        if self.sbu_unit_id:
            business_unit_filter = "AND hre.sbu_unit_id = {0}".format(self.sbu_unit_id.id)
            

        data_sql = """
                    SELECT hre.id_card_no AS id_card_no, easl.ac_sign_in AS check_in_time, easl.ac_sign_out AS check_out_time, easl.overtime AS overtime_hours_time, easl.date AS attendance_date,
                    hre.name AS employee_name, hd.name->>'en_US' AS dept_name, sl.name AS loc_name
                    FROM employee_attendance_sheet_line easl
                    LEFT JOIN hr_employee hre ON hre.id = easl.employee_id
                    LEFT JOIN hr_employee_type hret ON hret.id = hre.employee_type_id
                    LEFT JOIN hr_contract hc ON hc.employee_id = easl.employee_id
                    LEFT JOIN hr_department hd ON hd.id = hre.department_id
                    LEFT JOIN stock_location sl ON sl.id = hre.user_work_location_id
                        {8} JOIN (
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {7}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = hre.id
                    WHERE hc.state = 'open' AND DATE(easl.date) BETWEEN '{0}' AND '{1}' {2} {3} {4} {5} {6} AND easl.overtime > 0 AND easl.ovt_flag = '1'
                    ORDER BY easl.date, {9}
                    """.format(start_date, end_date,
                                emp_filter, dept_filter,
                                work_loc_filter, status_filter,
                                business_unit_filter, tags_filter,
                                tag_filter_join, order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()
        # data_list = []
        #
        # for d in data_res:
        #     emp_id = self.env['hr.employee'].browse(d['emp_id'])
        #     print(timedelta(hours=d['worked_hours']))
        #     time = str(timedelta(hours=d['worked_hours'])).rsplit(':', 1)[0]
        #     print(time)
        #     vals = {
        #         'employee_name': emp_id.display_name,
        #         'id_card_no': d['emp_id'],
        #         'attendance_date': d['attendance_date'],
        #         'company_name': self.env['res.company'].search([('id', '=', self.company_id.id)], limit=1).display_name,
        #         'loc_name': self.env['stock.location'].search([('id', '=', self.user_work_location_id.id)],
        #                                                       limit=1).display_name,
        #         'dept_name': self.env['hr.department'].search([('id', '=', self.department_id.id)],
        #                                                       limit=1).display_name,
        #         'check_in_time': d['check_in'],
        #         'check_out_time': d['check_out'],
        #         'overtime_hours_time': time,
        #     }
        #     data_list.append(vals)

        data = {
            'model': 'employee.overtime.report.wizard',
            'form': self.read()[0],
            'csr': data_res,
            'employee_id_card': employee_id_card,
            'employee_name': employee_name,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            # 'status_name': status_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data
