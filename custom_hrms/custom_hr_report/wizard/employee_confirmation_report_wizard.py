from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import datetime
from datetime import datetime, timedelta
import copy
from itertools import groupby

import xlsxwriter

import base64
from io import BytesIO


class EmployeeConfirmationReportWizard(models.TransientModel):
    _name = "employee.confirmation.report.wizard"
    _description = "Employee Confirmation Report Wizard"

    file_data = fields.Binary('Employee Confirmation Report')
    from_date = fields.Date(string='From Date', default=fields.Date.context_today)
    to_date = fields.Date(string='To Date', default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       default=lambda self: self._get_work_loc(),
                                       domain=lambda self: self._set_domain_work_loc())
    department_ids = fields.Many2many('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')

    category_ids = fields.Many2many('hr.employee.category', 'employee_confirmation_employee_category_rel', 
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
        if self.to_date < self.from_date:
            raise ValidationError(_('From date cannot be less than the to date.'))

    def employee_confirmation_report_pdf(self):
        from_date = self.from_date
        to_date = self.to_date
        user_work_location_id = self.user_work_location_id
        department_ids = self.department_ids
        employee_id = self.employee_id

        # get data from sql
        data = self.employee_confirmation_report_sql(from_date, to_date, user_work_location_id, department_ids, employee_id)

        return self.env.ref(
            'custom_hr_report.employee_confirmation_report_tmpl').with_context(landscape=False).report_action(self,
                                                                                                              data=data)

    def employee_confirmation_report_excel(self):
        from_date = self.from_date
        to_date = self.to_date
        user_work_location_id = self.user_work_location_id
        department_ids = self.department_ids
        employee_id = self.employee_id

        # get data from sql
        data = self.employee_confirmation_report_sql(from_date, to_date, user_work_location_id, department_ids, employee_id)

        file_name = "Employee Confirmation Report.xlsx"
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

        sheet.merge_range(0, 0, 0, 8, "{0}".format(data['form']['company_id'][1]), format0)
        sheet.merge_range(1, 0, 2, 8, "Employee Confirmation Report", format0)

        sheet.merge_range(3, 0, 3, 3,'From Date: {0}'.format(datetime.strptime(str(from_date), '%Y-%m-%d').strftime('%d-%b-%Y')),format1)
        sheet.merge_range(4, 0, 4, 3, 'To Date: {0}'.format(datetime.strptime(str(to_date), '%Y-%m-%d').strftime('%d-%b-%Y')),format1)
        sheet.merge_range(5, 0, 5, 3, 'Work/Job Location: {0}'.format(data['work_location_name']), format1)
        sheet.merge_range(6, 0, 6, 3, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)

        sheet.merge_range(3, 4, 3, 8, 'Employee: {0}'.format(data['emp_name']), format1)
        sheet.merge_range(4, 4, 4, 8, 'Department: {0}'.format(data['dept_name']), format1)
        sheet.merge_range(5, 4, 5, 8, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)
        sheet.merge_range(6, 4, 6, 8, None, format1)

        sheet.write(7, 0, 'SL No.', format2)
        sheet.write(7, 1, 'Employee Name', format2)
        sheet.write(7, 2, 'Employee ID', format2)
        sheet.write(7, 3, 'Joining Date', format2)
        sheet.write(7, 4, 'Work Location', format2)
        sheet.write(7, 5, 'Department', format2)
        sheet.write(7, 6, 'Designation', format2)
        sheet.write(7, 7, 'Confirmation Date', format2)
        sheet.write(7, 8, 'Remarks', format2)


        row = 8
        col = 0
        sl_no = 1

        for line in data['csr']:
            sheet.write(row, col, sl_no, format5)
            col = col + 1
            sheet.write(row, col, line['emp_name'], format5)
            col = col + 1
            sheet.write(row, col, line['id_card_no'], format5)
            col = col + 1
            sheet.write(row, col, datetime.strptime(str(line['joining_date']), '%Y-%m-%d').strftime('%d-%b-%Y'), format5)
            col = col + 1
            sheet.write(row, col, line['loc_name'], format5)
            col = col + 1
            sheet.write(row, col, line['dept_name'], format5)
            col = col + 1
            sheet.write(row, col, line['desig_name'], format5)
            col = col + 1
            sheet.write(row, col, datetime.strptime(str(line['confirmation_date']), '%Y-%m-%d').strftime('%d-%b-%Y'), format5)

            row = row + 1
            col = 0

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Employee Confirmation Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=employee.confirmation.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def employee_confirmation_report_sql(self, from_date, to_date, user_work_location_id, department_ids, employee_id):
        work_loc_filter = ""
        dept_filter = ""
        emp_filter = ""
        work_location_name = "All"
        dept_name = "All"
        emp_name = "All"
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"
        order_by = "tbl1.emp_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "tbl1.id_card_no"
        print(order_by)


        if user_work_location_id:
            work_loc_filter = "AND hre.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.name

        if len(department_ids) > 1:
            dept_filter = "AND hre.department_id in {0}".format(tuple(department_ids.ids))
            dept_name = ", ".join([d.name for d in department_ids])
        elif len(department_ids) == 1:
            dept_filter = "AND hre.department_id = %s" % department_ids.id
            dept_name = department_ids.name

        if employee_id:
            emp_filter = "AND hre.id = %s" % employee_id.id
            emp_name = employee_id.name

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND hre.sbu_unit_id = {0}".format(self.sbu_unit_id.id)  

        data_sql = """
                    SELECT tbl1.confirmation_date, tbl1.emp_id, tbl1.emp_name, tbl1.id_card_no, tbl1.joining_date, sl.name AS loc_name, hd.name->>'en_US' AS dept_name,hj.name->>'en_US' AS desig_name 
                    FROM (
                        SELECT date_of_confirmation AS confirmation_date, hre.id AS emp_id, hre.name AS emp_name, hre.department_id, hre.job_id, hre.user_work_location_id, hre.id_card_no, hre.initial_employment_date AS joining_date
                        FROM hr_employee hre
                        JOIN hr_contract hc ON hc.id = hre.contract_id
                        {7} JOIN (   
                                SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                JOIN hr_employee_category etag on etag.id=ecr.category_id
                                {6}
                                GROUP BY emp_id
                            ) emp_tag ON emp_tag.emp_id = hre.id
                        WHERE hc.state = 'open' AND date_of_confirmation BETWEEN '{0}' AND '{1}' {2} {3} {4} {5}
                    ) tbl1
                    LEFT JOIN hr_department hd ON hd.id = tbl1.department_id
                    LEFT JOIN hr_job hj ON hj.id = tbl1.job_id
                    LEFT JOIN stock_location sl ON sl.id = tbl1.user_work_location_id
                    --  ORDER BY tbl1.confirmation_date, tbl1.emp_name
                    ORDER BY tbl1.confirmation_date, {8}
                    """.format(from_date, to_date,
                                work_loc_filter, dept_filter, 
                                emp_filter, business_unit_filter, 
                                tags_filter, tag_filter_join, 
                                order_by)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        data = {
            'model': "employee.confirmation.report.wizard",
            'form': self.read()[0],
            'csr': data_res,
            'work_location_name': work_location_name,
            'dept_name': dept_name,
            'emp_name': emp_name,
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data
