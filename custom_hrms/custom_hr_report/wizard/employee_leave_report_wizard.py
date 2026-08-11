from odoo import models, fields, api, _
import datetime
from datetime import datetime
from itertools import groupby
import xlsxwriter

import base64
from io import BytesIO


class EmployeeLeaveReportWizard(models.Model):
    _name = 'employee.leave.report.wizard'
    _description = 'Employee Leave Report Wizard'

    file_data = fields.Binary('Employee Leave Report')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Location', default=lambda self: self._get_work_loc(),
                                       domain=lambda self: self._set_domain_work_loc())
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date', default=fields.Date.context_today)
    leave_type_id = fields.Many2one('hr.leave.type', string='Time Off Type')
    status = fields.Selection([
        ('draft', 'To Submit'),
        ('confirm', 'To Approve'),
        ('confirm2', 'Department approved'),
        ('confirm3', 'HR approved'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved'),
        ('cancel', 'Cancelled'),
    ], string='Status')

    category_ids = fields.Many2many('hr.employee.category', 'employee_leave_employee_category_rel', 
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

    def employee_leave_report_pdf(self):
        start_date = self.start_date
        end_date = self.end_date
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id
        leave_type_id = self.leave_type_id
        status = self.status

        # get data from sql
        data = self.employee_leave_report_sql(start_date, end_date, department_id, user_work_location_id, leave_type_id, status)

        return self.env.ref(
            'custom_hr_report.employee_leave_report_tmpl').with_context(landscape=False).report_action(self, data=data)


    def employee_leave_report_excel(self):
        start_date = self.start_date
        end_date = self.end_date
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id
        leave_type_id = self.leave_type_id
        status = self.status

        # get data from sql
        data = self.employee_leave_report_sql(start_date, end_date, department_id, user_work_location_id, leave_type_id, status)

        file_name = "Leave Report (Date Wise).xlsx"
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

        sheet.merge_range(0, 0, 0, 7, "{0}".format(data['form']['company_id'][1]), format0)
        sheet.merge_range(1, 0, 1, 7, "Leave Report (Date Wise)", format0)

        sheet.merge_range(2, 0, 2, 3, 'From Date: {0}'.format(datetime.strptime(str(start_date), '%Y-%m-%d').strftime('%d-%b-%Y')), format1)
        sheet.merge_range(3, 0, 3, 3, 'To Date: {0}'.format(datetime.strptime(str(end_date), '%Y-%m-%d').strftime('%d-%b-%Y')), format1)
        sheet.merge_range(4, 0, 4, 3, 'Work/Job Location: {0}'.format(data['work_loc_name']), format1)
        sheet.merge_range(5, 0, 5, 3, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)

        sheet.merge_range(2, 4, 2, 7, 'Leave Type: {0}'.format(data['leave_type_name']), format1)
        sheet.merge_range(3, 4, 3, 7, 'Department: {0}'.format(data['dept_name']), format1)
        sheet.merge_range(4, 4, 4, 7, 'Status: {0}'.format(data['status_name']), format1)
        sheet.merge_range(5, 4, 5, 7, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)

        sheet.write(6, 0, 'Employee', format2)
        sheet.write(6, 1, 'Designation', format2)
        sheet.write(6, 2, 'Employee ID', format2)
        sheet.write(6, 3, 'Start Date', format2)
        sheet.write(6, 4, 'End Date', format2)
        sheet.write(6, 5, 'Duration (Days)', format2)
        sheet.write(6, 6, 'Status', format2)
        sheet.write(6, 7, 'Time Off Type', format2)


        row = 7
        col = 0

        for line in data['csr']:


            sheet.write(row, col, line['emp_name'], format5)
            col = col + 1
            sheet.write(row, col, line['designation'], format5)
            col = col + 1
            sheet.write(row, col, line['id_no'], format5)
            col = col + 1
            sheet.write(row, col, datetime.strptime(str(line['start_date']), '%Y-%m-%d').strftime('%d-%b-%Y'), format5)
            col = col + 1
            sheet.write(row, col, datetime.strptime(str(line['end_date']), '%Y-%m-%d').strftime('%d-%b-%Y'), format5)
            col = col + 1
            sheet.write(row, col, line['duration'], format5)
            col = col + 1
            sheet.write(row, col, line['status'], format5)
            col = col + 1
            sheet.write(row, col, line['leave_type'], format5)

            row = row + 1
            col = 0


        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Leave Report (Date Wise)',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.leave.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_leave_report_sql(self, start_date, end_date, department_id, user_work_location_id, leave_type_id, status):
        dept_filter = ""
        work_loc_filter = ""
        leave_type_filter = ""
        status_filter = ""
        dept_name = "All"
        work_location_name = "All"
        leave_type_name = "All"
        status_name = "All"

        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"

        order_by = "he.name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "he.id_card_no"
        print(order_by)



        if department_id:
            dept_filter = "AND he.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            work_loc_filter = "AND he.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if leave_type_id:
            leave_type_filter = "AND hlt.id = %s" % leave_type_id.id
            leave_type_name = leave_type_id.display_name

        if status:
            status_filter = "AND hl.state = '%s'" % status
            status_name = dict(self._fields['status'].selection).get(status)

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND he.sbu_unit_id = {0}".format(self.sbu_unit_id.id)  

        data_sql = """
                    SELECT he.name AS emp_name,he.department_id,he.user_work_location_id,hj.name->>'en_US' AS designation, he.id_card_no AS id_no, mtbl.start_date, mtbl.end_date,
                    (CASE WHEN ((mtbl.end_date - mtbl.start_date) + 1) > mtbl.no_of_days THEN mtbl.no_of_days ELSE ((mtbl.end_date - mtbl.start_date) + 1) END) AS duration,
                    mtbl.status AS status, hlt.name AS leave_type
                    FROM (
                        SELECT hl.employee_id, hl.job_id, hl.holiday_status_id, 
                        (CASE WHEN DATE(hl.date_from) < '{0}' THEN '{0}' ELSE DATE(hl.date_from) END) AS start_date,
                        (CASE WHEN DATE(hl.date_to) > '{1}' THEN '{1}' ELSE DATE(hl.date_to) END) AS end_date,
                        COALESCE(SUM(hl.number_of_days), 0) AS no_of_days,
                        (CASE WHEN hl.state = 'draft' THEN 'To Submit' ELSE
                        CASE WHEN hl.state = 'confirm' THEN 'To Approve' ELSE
                        CASE WHEN hl.state = 'refuse' THEN 'Refused' ELSE
                        CASE WHEN hl.state = 'validate1' THEN 'Second Approval' ELSE
                        CASE WHEN hl.state = 'validate' THEN 'Approved' ELSE
                        CASE WHEN hl.state = 'cancel' THEN 'Cancelled' ELSE ''
                        END END END END END END) AS status
                        FROM hr_leave hl
                        WHERE hl.request_date_from >= '{0}' AND hl.request_date_to <= '{1}' {5}
                        GROUP BY hl.employee_id, hl.job_id, hl.holiday_status_id, hl.date_from, hl.state, hl.date_to
                    ) mtbl
                    LEFT JOIN hr_employee he ON he.id = mtbl.employee_id
                    LEFT JOIN hr_job hj ON hj.id = mtbl.job_id
                    LEFT JOIN hr_leave_type hlt ON hlt.id = mtbl.holiday_status_id 
                    {8} JOIN (
                            SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                            JOIN hr_employee_category etag on etag.id=ecr.category_id
                            {7}
                            GROUP BY emp_id
                        ) emp_tag ON emp_tag.emp_id = he.id
                    WHERE (1=1) {2} {3} {4} {6}
                    --  ORDER BY mtbl.start_date, mtbl.end_date
                    ORDER BY mtbl.start_date, mtbl.end_date, {9}
                    """.format(start_date, end_date,
                                work_loc_filter, dept_filter,
                                leave_type_filter, status_filter,
                                business_unit_filter, tags_filter,
                                tag_filter_join, order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        data = {
            'model': "employee.leave.report.wizard",
            'form': self.read()[0],
            'csr': data_res,
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'leave_type_name': leave_type_name,
            'status_name': status_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data
