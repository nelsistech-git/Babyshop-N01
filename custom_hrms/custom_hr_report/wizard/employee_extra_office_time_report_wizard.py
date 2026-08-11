from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import xlsxwriter

import base64
from io import BytesIO


class EmployeeExtraOfficeTimetimeReportWizard(models.TransientModel):
    _name = "employee.extra.office.time.report.wizard"
    _description = "Employee Extra Office Time Report Wizard"

    file_data = fields.Binary('')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    #department_id = fields.Many2one('hr.department', string='Department/Sub-Section')
    department_ids = fields.Many2many('hr.department', string='Department/Section')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    status = fields.Many2one('hr.employee.type',string="Status")

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

    def employee_extra_ot_2h_time_report_pdf(self):
        rpt_type = 'two_hours' #2hours change to 3hours in sql
        # get data from sql
        #data = self.employee_overtime_report_sql(start_date, end_date, employee_id, department_id, user_work_location_id,status, rpt_type)
        data = {
            'ftr_id': self.id,
            'rpt_type': rpt_type
        }

        return self.env.ref(
            'custom_hr_report.extra_office_time_2h_report_id').with_context(landscape=False).report_action(self, data=data)

    def employee_extra_ot_more2h_time_report_pdf(self):
        # start_date = self.start_date
        # end_date = self.end_date
        # employee_id = self.employee_id
        # department_id = self.department_id
        # user_work_location_id = self.user_work_location_id
        # status = self.status
        rpt_type = 'two_hours_more'
        # get data from sql
        #data = self.employee_overtime_report_sql(start_date, end_date, employee_id, department_id, user_work_location_id,status, rpt_type)

        # get data from sql
        # data = self.employee_overtime_report_sql(start_date, end_date, employee_id, department_id, user_work_location_id,status, rpt_type)
        data = {
            'ftr_id': self.id,
            'rpt_type': rpt_type
        }

        return self.env.ref(
            'custom_hr_report.extra_office_time_more2h_report_id').with_context(landscape=False).report_action(self, data=data)
    #unused
    def employee_overtime_report_excel(self):
        start_date = self.start_date
        end_date = self.end_date
        employee_id = self.employee_id
        department_ids = self.department_ids
        user_work_location_id = self.user_work_location_id
        status = self.status

        # get data from sql
        data = self.employee_overtime_report_sql(start_date, end_date, employee_id, department_ids, user_work_location_id,status)

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
            sheet.merge_range(5, 0, 5, 2, None, format1)

            sheet.merge_range(3, 3, 3, 5, 'Work/Job Location: {0}'.format(data['work_loc_name']), format1)
            sheet.merge_range(4, 3, 4, 5, 'Department: {0}'.format(data['dept_name']), format1)
            sheet.merge_range(5, 3, 5, 5, 'Employee Name: {0}'.format(data['employee_name']), format1)

            sheet.write(6, 0, 'Sl.', format5)
            sheet.write(6, 1, 'Date', format1)
            sheet.write(6, 2, 'Employee Name', format1)
            sheet.write(6, 3, 'Check In', format1)
            sheet.write(6, 4, 'Check Out', format1)
            sheet.write(6, 5, 'Overtime Hours', format1)

            row = 7
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
            sheet.merge_range(5, 0, 5, 2, None, format1)
            sheet.merge_range(6, 0, 6, 2, None, format1)

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

    def employee_overtime_report_sql(self, rpt_type):
        start_date = self.start_date
        end_date = self.end_date
        employee_id = self.employee_id
        department_ids = self.department_ids
        user_work_location_id = self.user_work_location_id
        status = self.status

        emp_filter = ""
        dept_filter = ""
        dept_single_filter = ""
        work_loc_filter = ""
        status_filter = ""
        dept_name = "All"
        work_location_name = "All"
        employee_name = "All"
        employee_id_card = ""

        # if department_id:
        #     dept_filter = "AND hre.department_id = %s" % department_id.id
        #     dept_single_filter = "where id = %s" % department_id.id
        #     dept_name = department_id.display_name

        if len(department_ids) > 1:
            dept_filter = "AND hre.department_id in {0}".format(tuple(department_ids.ids))
            dept_single_filter = "where id in {0}".format(tuple(department_ids.ids))
            dept_name = ", ".join([d.name for d in department_ids])
        elif len(department_ids) == 1:
            dept_filter = "AND hre.department_id = %s" % department_ids.id
            dept_single_filter = "where id = %s" % department_ids.id
            dept_name = department_ids.name

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
        data_sql = ''

        # if rpt_type == 'two_hours':
        #     data_sql = """
        #                 SELECT hre.id_card_no AS id_card_no,
        #                 hre.name AS employee_name,
        #                 hre.initial_employment_date AS join_date,
        #                 hd.name AS dept_name,
        #                 desig.name AS designation,
        #                 sl.name AS loc_name,
        #                 COALESCE(ROUND(hc.wage, 2), 0) AS basic,
        #                 COUNT(easl.id) AS nod,
        #                 COALESCE(SUM(CASE WHEN easl.overtime > 2 THEN 2 ELSE easl.overtime END), 0) AS ot_hour, hre.department_id
        #                 FROM employee_attendance_sheet_line easl
        #                 LEFT JOIN hr_employee hre ON hre.id = easl.employee_id
        #                 LEFT JOIN hr_employee_type hret ON hret.id = hre.employee_type_id
        #                 LEFT JOIN hr_contract hc ON hc.employee_id = easl.employee_id
        #                 LEFT JOIN hr_department hd ON hd.id = hre.department_id
        #                 LEFT JOIN hr_job desig ON desig.id = hre.job_id
        #                 LEFT JOIN stock_location sl ON sl.id = hre.work_location_id
        #                 WHERE DATE(easl.date) BETWEEN '{0}' AND '{1}' {2} {3} {4} {5} AND easl.ovt_flag = '1' AND easl.overtime > 0 AND easl.status is null
        #                 GROUP BY hre.id_card_no, hre.name, hre.initial_employment_date, hd.name,desig.name,sl.name,hc.wage, hre.department_id
        #                 ORDER BY hd.name,sl.name,hre.id_card_no
        #                 """.format(start_date, end_date, emp_filter, dept_filter, work_loc_filter, status_filter)
        #     self.env.cr.execute(data_sql)
        #     data_res = self.env.cr.dictfetchall()
        #     print(data_res)
            # rint(data_res)

        data_res = []
        self.env.cr.execute("""select id,name->>'en_US' as name, complete_name from hr_department {0} """.format(dept_single_filter))
        dept_wise_over_time_list = self.env.cr.dictfetchall()
        # print(dept_list)
        for rec in dept_wise_over_time_list:
            # print(rec['id'])
            if rpt_type == 'two_hours':
                data_sql = """
                            SELECT hre.id_card_no AS id_card_no, 
                            hre.name AS employee_name,
                            hre.initial_employment_date AS join_date,
                            hd.name->>'en_US' AS dept_name,
                            desig.name->>'en_US' AS designation,
                            sl.name AS loc_name,
                            COALESCE(ROUND(hc.wage, 2), 0) AS basic,
                            COUNT(easl.id) AS nod,
                            COALESCE(SUM(CASE WHEN easl.overtime > 3 THEN 3 ELSE easl.overtime END), 0) AS ot_hour
                            FROM employee_attendance_sheet_line easl
                            LEFT JOIN hr_employee hre ON hre.id = easl.employee_id
                            LEFT JOIN hr_employee_type hret ON hret.id = hre.employee_type_id
                            LEFT JOIN hr_contract hc ON hc.employee_id = easl.employee_id
                            LEFT JOIN hr_department hd ON hd.id = hre.department_id
                            LEFT JOIN hr_job desig ON desig.id = hre.job_id
                            LEFT JOIN stock_location sl ON sl.id = hre.user_work_location_id
                            WHERE DATE(easl.date) BETWEEN '{0}' AND '{1}' {2} and hre.department_id = {3} {4} {5} AND easl.ovt_flag = '1' AND easl.overtime > 3 AND easl.status is null
                            GROUP BY hre.id_card_no, hre.name, hre.initial_employment_date, hd.name,desig.name,sl.name,hc.wage
                            ORDER BY hd.name,sl.name,hre.id_card_no
                            """.format(start_date, end_date, emp_filter, rec['id'], work_loc_filter, status_filter)
                self.env.cr.execute(data_sql)
                data_res = self.env.cr.dictfetchall()
                if data_res:
                    rec['item_list'] = data_res
            elif rpt_type == 'two_hours_more':
                data_sql = """
                            SELECT hre.id_card_no AS id_card_no, 
                            hre.name AS employee_name,
                            hre.initial_employment_date AS join_date,
                            hd.name->>'en_US' AS dept_name,
                            desig.name->>'en_US' AS designation,
                            sl.name AS loc_name,
                            COALESCE(ROUND(hc.wage, 2), 0) AS basic,
                            COUNT(easl.id) AS nod,
                            COALESCE(SUM(CASE WHEN easl.overtime > 3 THEN (easl.overtime - 3) ELSE 0 END), 0) AS ot_hour
                            FROM employee_attendance_sheet_line easl
                            LEFT JOIN hr_employee hre ON hre.id = easl.employee_id
                            LEFT JOIN hr_employee_type hret ON hret.id = hre.employee_type_id
                            LEFT JOIN hr_contract hc ON hc.employee_id = easl.employee_id
                            LEFT JOIN hr_department hd ON hd.id = hre.department_id
                            LEFT JOIN hr_job desig ON desig.id = hre.job_id
                            LEFT JOIN stock_location sl ON sl.id = hre.user_work_location_id
                            WHERE DATE(easl.date) BETWEEN '{0}' AND '{1}' {2} and hre.department_id = {3} {4} {5} AND easl.ovt_flag = '1' AND easl.overtime > 3 AND easl.status is null
                            GROUP BY hre.id_card_no, hre.name, hre.initial_employment_date, hd.name,desig.name,sl.name,hc.wage
                            ORDER BY hd.name,sl.name,hre.id_card_no
                            """.format(start_date, end_date, emp_filter, rec['id'], work_loc_filter,
                                       status_filter)
                self.env.cr.execute(data_sql)
                data_res = self.env.cr.dictfetchall()
                if data_res:
                    rec['item_list'] = data_res
        #print(dept_wise_over_time_list)
        data = {
            'model': 'employee.overtime.report.wizard',
            'form': self.read()[0],
            'csr': dept_wise_over_time_list,
            'employee_id_card': employee_id_card,
            'employee_name': employee_name,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            # 'status_name': status_name,
        }
        return data
