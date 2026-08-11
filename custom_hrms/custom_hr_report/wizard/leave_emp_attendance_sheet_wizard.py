from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import datetime
from datetime import datetime, timedelta
import copy
from itertools import groupby

import xlsxwriter

import base64
from io import BytesIO


def get_years():
    year_list = []
    crn_year = datetime.now().year
    for i in range(2021, crn_year + 5):
        year_list.append((str(i), str(i)))
    return year_list


class LeavePhDailyAttendanceSheetWizard(models.TransientModel):
    _name = "leave.emp.attendance.sheet.wizard"
    _description = "Leave Employee Attendance Sheet Wizard"

    file_data = fields.Binary('Leave Employee Attendance Sheet Wizard')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                        default=lambda self: self._get_work_loc(),
                                        domain=lambda self: self._set_domain_work_loc())
    department_ids = fields.Many2many('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    status = fields.Selection(
        [('present', 'Present')
        ], string='Status', default='present')

    category_ids = fields.Many2many('hr.employee.category', 'leave_emp_attendance_employee_category_rel', 
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

    @api.constrains('from_date', 'to_date')
    def date_constrains(self):
        for rec in self:
            if rec.to_date < rec.from_date:
                raise ValidationError(_('From date cannot be greater than the end date.'))

    def leave_emp_attendance_sheet_excel(self):
        from_date = self.from_date
        to_date = self.to_date
        user_work_location_id = self.user_work_location_id
        department_ids = self.department_ids
        employee_id = self.employee_id
        status = self.status

        # get data from sql
        #data = self.daily_attendance_sheet_sql(from_date, to_date, work_location_id, department_ids, employee_id, status)
        data = self.leave_emp_attendance_sheet_sql()

        from_date = datetime.strptime(str(from_date), '%Y-%m-%d').strftime('%d-%b-%Y')
        to_date = datetime.strptime(str(to_date), '%Y-%m-%d').strftime('%d-%b-%Y')

        file_name = "Leave Employee Attendance Sheet (%s - %s).xlsx" % (data['form']['from_date'], data['form']['to_date'])
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

        sheet = workbook.add_worksheet('Leave Employee Attendance Sheet')

        emp_id = -1
        total_emp = 0
        total_present = 0
        total_absent = 0
        total_late_in = 0
        total_early_out = 0
        total_leave = 0
        total_ph = 0
        total_wk = 0

        if employee_id:
            sheet.merge_range(0, 0, 0, 9, "{0}".format(data['form']['company_id'][1]), format0)
            sheet.merge_range(1, 0, 2, 9, "Leave Employee Attendance Sheet", format0)

            sheet.merge_range(3, 0, 3, 3, 'From Date: {0}'.format(from_date), format1)
            sheet.merge_range(4, 0, 4, 3, 'To Date: {0}'.format(to_date), format1)
            sheet.merge_range(5, 0, 5, 3, 'Employee ID: {0}'.format(employee_id.id_card_no), format1)
            sheet.merge_range(6, 0, 6, 3, 'Employee: {0}'.format(employee_id.name), format1)
            sheet.merge_range(7, 0, 7, 3, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)

            sheet.merge_range(3, 4, 3, 9, 'Work Location: {0}'.format(employee_id.user_work_location_id.name), format1)
            sheet.merge_range(4, 4, 4, 9, 'Department: {0}'.format(employee_id.department_id.name), format1)
            sheet.merge_range(5, 4, 5, 9, 'Designation: {0}'.format(employee_id.job_id.name), format1)
            sheet.merge_range(6, 4, 6, 9, 'Joining Date: {0}'.format(data['emp_joining_date']), format1)
            sheet.merge_range(7, 4, 7, 9, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)

            sheet.write(8, 0, 'Date', format2)
            sheet.write(8, 1, 'Check-in', format2)
            sheet.write(8, 2, 'Check-out', format2)
            sheet.write(8, 3, 'Overtime', format2)
            sheet.write(8, 4, 'Late-in', format2)
            sheet.write(8, 5, 'Early Out', format2)
            sheet.write(8, 6, 'Auto/Manual', format2)
            sheet.write(8, 7, 'Manual Reason', format2)
            sheet.write(8, 8, 'Status', format2)
            sheet.write(8, 9, 'Note', format2)

            row = 9
            col = 0

            for rec in data['csr']:
                if emp_id != rec['emp_id']:
                    total_emp = total_emp + 1
                if (not data['form']['status'] or data['form']['status'] == 'present') and not rec['main_status']:
                    total_present = total_present + 1
                if (not data['form']['status'] or data['form']['status'] == 'ab') and rec['main_status'] == 'ab':
                    total_absent = total_absent + 1
                if (not data['form']['status'] or data['form']['status'] == 'late_in') and rec['late_in'] > 0:
                    total_late_in = total_late_in + 1
                if (not data['form']['status'] or data['form']['status'] == 'early_out') and rec['diff_time'] > 0:
                    total_early_out = total_early_out + 1
                if (not data['form']['status'] or data['form']['status'] == 'leave') and rec['main_status'] == 'leave':
                    total_leave = total_leave + 1
                if rec['main_status'] == 'ph':
                    total_ph = total_ph + 1
                if rec['main_status'] == 'weekend':
                    total_wk = total_wk + 1

                sheet.write(row, col, datetime.strptime(str(rec['date']), '%Y-%m-%d').strftime('%d-%b-%Y'), format5)
                sheet.write(row, col + 1,
                            str(timedelta(hours=int(rec['check_in']), minutes=(rec['check_in'] * 60) % 60, seconds=00)),
                            format5)
                if rec['punch_count'] != 1:
                    sheet.write(row, col + 2,
                                str(timedelta(hours=int(rec['check_out']), minutes=(rec['check_out'] * 60) % 60,
                                              seconds=00)), format5)
                else:
                    sheet.write(row, col + 2, None, format5)
                sheet.write(row, col + 3,
                            str(timedelta(hours=int(rec['overtime']), minutes=(rec['overtime'] * 60) % 60,
                                          seconds=00)), format5)
                sheet.write(row, col + 4,
                            str(timedelta(hours=int(rec['late_in']), minutes=(rec['late_in'] * 60) % 60, seconds=00)),
                            format5)
                sheet.write(row, col + 5,
                            str(timedelta(hours=int(rec['diff_time']), minutes=(rec['diff_time'] * 60) % 60,
                                          seconds=00)), format5)

                sheet.write(row, col + 6, rec['att_type'], format5)
                sheet.write(row, col + 7, rec['manual_reason'], format5)
                sheet.write(row, col + 8, rec['status'], format5)
                sheet.write(row, col + 9, str(rec['leave_name'])+': '+ str(rec['note']) if rec['note'] else str(rec['leave_name']), format5)

                row = row + 1
                emp_id = rec['emp_id']

            final_row = row + 2
            final_col = 0
            sheet.write(final_row, final_col, 'Total Employee:', format8)
            sheet.write(final_row, final_col + 1, total_emp, format9)
            final_row = final_row + 1
            if not data['form']['status'] or data['form']['status'] == 'present':
                sheet.write(final_row, final_col, 'Total Present:', format8)
                sheet.write(final_row, final_col + 1, total_present, format9)
                final_row = final_row + 1
            if not data['form']['status'] or data['form']['status'] == 'ab':
                sheet.write(final_row, final_col, 'Total Absent:', format8)
                sheet.write(final_row, final_col + 1, total_absent, format9)
                final_row = final_row + 1
            if not data['form']['status'] or data['form']['status'] == 'late_in':
                sheet.write(final_row, final_col, 'Total Late In:', format8)
                sheet.write(final_row, final_col + 1, total_late_in, format9)
                final_row = final_row + 1
            if not data['form']['status'] or data['form']['status'] == 'early_out':
                sheet.write(final_row, final_col, 'Total Early Out:', format8)
                sheet.write(final_row, final_col + 1, total_early_out, format9)
                final_row = final_row + 1
            if not data['form']['status'] or data['form']['status'] == 'leave':
                sheet.write(final_row, final_col, 'Total Leave:', format8)
                sheet.write(final_row, final_col + 1, total_leave, format9)
                final_row = final_row + 1
            sheet.write(final_row, final_col, 'Total Weekend:', format8)
            sheet.write(final_row, final_col + 1, total_wk, format9)
            final_row = final_row + 1
            sheet.write(final_row, final_col, 'Total Public Holiday:', format8)
            sheet.write(final_row, final_col + 1, total_ph, format9)

        else:
            sheet.merge_range(0, 0, 0, 14, "{0}".format(data['form']['company_id'][1]), format0)
            sheet.merge_range(1, 0, 2, 14, "Leave Employee Attendance Sheet", format0)

            sheet.merge_range(3, 0, 3, 5, 'From Date: {0}'.format(from_date), format1)
            sheet.merge_range(4, 0, 4, 5, 'To Date: {0}'.format(to_date), format1)
            sheet.merge_range(5, 0, 5, 5, 'Work/Job Location: {0}'.format(data['work_location_name']), format1)
            sheet.merge_range(6, 0, 6, 5, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)

            sheet.merge_range(3, 6, 3, 14, 'Employee: {0}'.format(data['emp_name']), format1)
            sheet.merge_range(4, 6, 4, 14, 'Department: {0}'.format(data['dept_name']), format1)
            sheet.merge_range(5, 6, 5, 14, 'Status: {0}'.format(data['status_name']), format1)
            sheet.merge_range(6, 6, 6, 14, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)



            sheet.write(7, 0, 'Date', format2)
            sheet.write(7, 1, 'Employee', format2)
            sheet.write(7, 2, 'Employee ID', format2)
            sheet.write(7, 3, 'Work Location', format2)
            sheet.write(7, 4, 'Department', format2)
            sheet.write(7, 5, 'Designation', format2)
            sheet.write(7, 6, 'Check-in', format2)
            sheet.write(7, 7, 'Check-out', format2)
            sheet.write(7, 8, 'Overtime', format2)
            sheet.write(7, 9, 'Late-in', format2)
            sheet.write(7, 10, 'Early Out', format2)
            sheet.write(7, 11, 'Auto/Manual', format2)
            sheet.write(7, 12, 'Manual Reason', format2)
            sheet.write(7, 13, 'Status', format2)
            sheet.write(7, 14, 'Note', format2)

            row = 8
            col = 0

            for rec in data['csr']:
                if emp_id != rec['emp_id']:
                    total_emp = total_emp + 1
                if (not data['form']['status'] or data['form']['status'] == 'present') and not rec['main_status']:
                    total_present = total_present + 1
                if (not data['form']['status'] or data['form']['status'] == 'ab') and rec['main_status'] == 'ab':
                    total_absent = total_absent + 1
                if (not data['form']['status'] or data['form']['status'] == 'late_in') and rec['late_in'] > 0:
                    total_late_in = total_late_in + 1
                if (not data['form']['status'] or data['form']['status'] == 'early_out') and rec['diff_time'] > 0:
                    total_early_out = total_early_out + 1
                if (not data['form']['status'] or data['form']['status'] == 'leave') and rec['main_status'] == 'leave':
                    total_leave = total_leave + 1
                if rec['main_status'] == 'ph':
                    total_ph = total_ph + 1
                if rec['main_status'] == 'weekend':
                    total_wk = total_wk + 1

                sheet.write(row, col, datetime.strptime(str(rec['date']), '%Y-%m-%d').strftime('%d-%b-%Y'), format5)
                sheet.write(row, col + 1, rec['emp_name'], format5)
                sheet.write(row, col + 2, rec['id_card_no'], format5)
                sheet.write(row, col + 3, rec['loc_name'], format5)
                sheet.write(row, col + 4, rec['dept_name'], format5)
                sheet.write(row, col + 5, rec['desig_name'], format5)
                sheet.write(row, col + 6, str(timedelta(hours=int(rec['check_in']), minutes=(rec['check_in'] * 60) % 60,
                                                        seconds=00)), format5)
                if rec['punch_count'] != 1:
                    sheet.write(row, col + 7,
                                str(timedelta(hours=int(rec['check_out']), minutes=(rec['check_out'] * 60) % 60,
                                              seconds=00)), format5)
                else:
                    sheet.write(row, col + 7, None, format5)
                sheet.write(row, col + 8,
                            str(timedelta(hours=int(rec['overtime']), minutes=(rec['overtime'] * 60) % 60,
                                          seconds=00)), format5)
                sheet.write(row, col + 9, str(timedelta(hours=int(rec['late_in']), minutes=(rec['late_in'] * 60) % 60,
                                                        seconds=00)), format5)
                sheet.write(row, col + 10,
                            str(timedelta(hours=int(rec['diff_time']), minutes=(rec['diff_time'] * 60) % 60,
                                          seconds=00)), format5)
                sheet.write(row, col + 11, rec['att_type'], format5)
                sheet.write(row, col + 12, rec['manual_reason'], format5)
                sheet.write(row, col + 13, rec['status'], format5)
                sheet.write(row, col + 14, str(rec['leave_name'])+': '+ str(rec['note']) if rec['note'] else str(rec['leave_name']), format5)

                row = row + 1
                emp_id = rec['emp_id']

            final_row = row + 2
            final_col = 0
            sheet.write(final_row, final_col, 'Total Employee:', format8)
            sheet.write(final_row, final_col + 1, total_emp, format9)
            final_row = final_row + 1
            if not data['form']['status'] or data['form']['status'] == 'present':
                sheet.write(final_row, final_col, 'Total Present:', format8)
                sheet.write(final_row, final_col + 1, total_present, format9)
                final_row = final_row + 1
            if not data['form']['status'] or data['form']['status'] == 'ab':
                sheet.write(final_row, final_col, 'Total Absent:', format8)
                sheet.write(final_row, final_col + 1, total_absent, format9)
                final_row = final_row + 1
            if not data['form']['status'] or data['form']['status'] == 'late_in':
                sheet.write(final_row, final_col, 'Total Late In:', format8)
                sheet.write(final_row, final_col + 1, total_late_in, format9)
                final_row = final_row + 1
            if not data['form']['status'] or data['form']['status'] == 'early_out':
                sheet.write(final_row, final_col, 'Total Early Out:', format8)
                sheet.write(final_row, final_col + 1, total_early_out, format9)
                final_row = final_row + 1
            if not data['form']['status'] or data['form']['status'] == 'leave':
                sheet.write(final_row, final_col, 'Total Leave:', format8)
                sheet.write(final_row, final_col + 1, total_leave, format9)
                final_row = final_row + 1
            sheet.write(final_row, final_col, 'Total Weekend:', format8)
            sheet.write(final_row, final_col + 1, total_wk, format9)
            final_row = final_row + 1
            sheet.write(final_row, final_col, 'Total Public Holiday:', format8)
            sheet.write(final_row, final_col + 1, total_ph, format9)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Leave Employee Attendance Sheet',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=leave.emp.attendance.sheet.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def leave_emp_attendance_sheet_sql(self):
        from_date = self.from_date
        to_date = self.to_date
        user_work_location_id = self.user_work_location_id
        department_ids = self.department_ids
        employee_id = self.employee_id
        status = self.status

        #--------------------
        work_loc_filter = ""
        work_loc_filter2 = ""
        dept_filter = ""
        dept_filter2 = ""
        emp_filter = ""
        emp_filter2 = ""
        work_location_name = "All"
        dept_name = "All"
        status_filter = ""
        status_name = "All"
        tags_filter = ""
        tag_filter_join = "LEFT"
        business_unit_filter = "" 

        order_by = "main_tbl.emp_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "main_tbl.id_card_no"
        # print(order_by)



        if user_work_location_id:
            work_loc_filter = "AND hre.user_work_location_id = %s" % user_work_location_id.id
            work_loc_filter2 = "AND hl.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.name

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

        if status == 'present':
            status_filter = "WHERE main_tbl.status IS NULL"
            status_name = 'Present'
        elif status == 'ab':
            status_filter = "WHERE main_tbl.status = 'ab'"
            status_name = 'Absent'
        elif status == 'late_in':
            status_filter = "WHERE main_tbl.late_in > 0"
            status_name = 'Late In'
        elif status == 'early_out':
            status_filter = "WHERE main_tbl.diff_time > 0 AND main_tbl.status IS NULL"
            status_name = 'Early Out'
        elif status == 'leave':
            status_filter = "WHERE main_tbl.status = 'leave'"
            status_name = 'Leave'

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   

        if self.sbu_unit_id:
            business_unit_filter = "AND hre.sbu_unit_id = {0}".format(self.sbu_unit_id.id)  

        data_sql = """
                    SELECT main_tbl.date, main_tbl.emp_id, main_tbl.emp_name, main_tbl.joining_date, COALESCE(main_tbl.id_card_no, '') AS id_card_no, COALESCE(main_tbl.loc_name, '') AS loc_name, COALESCE(main_tbl.dept_name, '') AS dept_name, COALESCE(main_tbl.desig_name, '') AS desig_name, COALESCE(main_tbl.ac_sign_in, 0) AS check_in, COALESCE(main_tbl.ac_sign_out, 0) AS check_out, COALESCE(main_tbl.punch_count, 0) AS punch_count,COALESCE(main_tbl.overtime, 0) AS overtime,
                         main_tbl.att_type, COALESCE(main_tbl.late_in, 0) AS late_in, COALESCE(main_tbl.diff_time, 0) AS diff_time, main_tbl.status AS main_status, main_tbl.manual_reason AS manual_reason,main_tbl.note AS note,leave_tbl.leave_name as leave_name,
                         CASE WHEN main_tbl.status IS NULL THEN 'Present' ELSE 
                         CASE WHEN main_tbl.status='ab' THEN 'Absent' ELSE 
                         CASE WHEN main_tbl.status='weekend' THEN 'Weekend' ELSE
                         CASE WHEN main_tbl.status='ph' THEN 'Public Holiday' ELSE
                         CASE WHEN main_tbl.status='leave' THEN leave_tbl.leave_name->>'en_US' ELSE ''
                         END END END END END AS status
                    FROM(
                        SELECT tbl1.date, hre.id AS emp_id, hre.name AS emp_name, hre.id_card_no,hre.initial_employment_date AS joining_date, tbl1.ac_sign_in, tbl1.ac_sign_out, tbl1.punch_count, tbl1.overtime, tbl1.att_type, 
                        sl.name AS loc_name, hd.name->>'en_US' AS dept_name,hj.name->>'en_US' AS desig_name, tbl1.late_in, tbl1.diff_time, tbl1.status, tbl1.manual_reason, tbl1.note
                        FROM (
                            SELECT eatsl.date, eatsl.employee_id, eatsl.ac_sign_in, eatsl.ac_sign_out, eatsl.overtime, eatsl.punch_count,
                            CASE WHEN eatsl.manual_flag=1 THEN COALESCE('Manual', '') ELSE 'Auto' END AS att_type, eatsl.late_in, eatsl.diff_time, eatsl.status, eatsl.manual_reason, eatsl.note
                            FROM employee_attendance_sheet_line eatsl
                            WHERE DATE(date) BETWEEN '{0}' AND '{1}'
                            GROUP BY eatsl.date, eatsl.employee_id, eatsl.ac_sign_in, eatsl.ac_sign_out, eatsl.status, eatsl.overtime, eatsl.punch_count, eatsl.late_in, eatsl.diff_time, eatsl.manual_flag, eatsl.manual_reason, eatsl.note
                            ORDER BY eatsl.date, eatsl.employee_id
                        ) tbl1
                        LEFT JOIN hr_employee hre ON hre.id = tbl1.employee_id
                        LEFT JOIN hr_contract hc ON hc.id = hre.contract_id
                        LEFT JOIN hr_department hd ON hd.id = hre.department_id
                        LEFT JOIN hr_job hj ON hj.id = hre.job_id
                        LEFT JOIN stock_location sl ON sl.id = hre.user_work_location_id
                        {11} JOIN (
                            SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                            JOIN hr_employee_category etag on etag.id=ecr.category_id
                            {9}
                            GROUP BY emp_id
                        ) emp_tag ON emp_tag.emp_id = hre.id
                        WHERE hc.state = 'open' {2} {3} {4} {10}
                        ORDER BY tbl1.date, hre.name
                    ) main_tbl
                    JOIN (
                        SELECT hld.leave_date, hl.employee_id, hlt.name AS leave_name
                        FROM hr_leave hl
                        JOIN hr_leave_details hld ON hld.leave_id = hl.id
                        JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                        WHERE hl.state='validate' AND DATE(hld.leave_date) BETWEEN '{0}' AND '{1}' {5} {6} {7}
                        ORDER BY hld.leave_date, hl.employee_id
                    ) leave_tbl ON leave_tbl.leave_date = main_tbl.date AND leave_tbl.employee_id = main_tbl.emp_id
                    {8}
                    --  ORDER BY main_tbl.date, main_tbl.emp_name
                    ORDER BY main_tbl.date, {12}
                    """.format(from_date, to_date,
                                work_loc_filter, dept_filter,
                                emp_filter, work_loc_filter2,
                                dept_filter2, emp_filter2,
                                status_filter, tags_filter,
                                business_unit_filter, tag_filter_join,
                                order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        emp_id_card_no = ""
        emp_name = "All"
        emp_work_loc_name = ""
        emp_dept_name = "All"
        emp_des_name = ""
        emp_joining_date = ""

        if employee_id:
            emp_id_card_no = employee_id.id_card_no
            emp_name = employee_id.name
            emp_work_loc_name = employee_id.user_work_location_id.name
            emp_dept_name = employee_id.department_id.name
            emp_des_name = employee_id.job_id.name
            emp_joining_date = employee_id.initial_employment_date

        data = {
            'model': "leave.emp.attendance.sheet.wizard",
            'form': self.read()[0],
            'csr': data_res,
            'work_location_name': work_location_name,
            'dept_name': dept_name,
            'status_name': status_name,
            'emp_id_card_no': emp_id_card_no,
            'emp_name': emp_name,
            'emp_work_loc_name': emp_work_loc_name,
            'emp_dept_name': emp_dept_name,
            'emp_des_name': emp_des_name,
            'emp_joining_date': emp_joining_date,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),

        }
        return data
