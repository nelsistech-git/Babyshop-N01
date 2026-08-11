from odoo import fields, models, api, _
import datetime
from calendar import monthrange
from datetime import datetime
from datetime import date
from itertools import groupby
from odoo.exceptions import ValidationError

import xlsxwriter

import base64
from io import BytesIO


def get_years():
    year_list = []
    crn_year = datetime.now().year
    for i in range(2022, crn_year + 5):
        year_list.append((str(i), str(i)))
    return year_list


class ProbationaryEmployeeReportWizard(models.TransientModel):
    _name = "probationary.employee.report.wizard"
    _description = "Probationary Employee Report Wizard"

    file_data = fields.Binary('Probationary Employee Report Wizard')
    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       default=lambda self: self._get_work_loc(),
                                       domain=lambda self: self._set_domain_work_loc())
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')

    category_ids = fields.Many2many('hr.employee.category', 'probationary_employee_employee_category_rel', 
                'selected_id', 'category_id', string='Tags')

    sbu_unit_id = fields.Many2one('hr.sbu.unit', string='Office/Business Unit')

    @api.model
    def _set_domain_work_loc(self):
        if self.env.user.user_work_location_id:
            return [('is_work_loc', '=', True), ('state', '=', 'done'), ('id', '=', self.env.user.user_work_location_id.id)]
        else:
            return [('is_work_loc', '=', True), ('state', '=', 'done')]

    @api.constrains('from_date', 'to_date')
    def date_constrains(self):
        from_date_year = datetime.strptime(str(self.from_date), '%Y-%m-%d').strftime('%Y')
        to_date_year = datetime.strptime(str(self.to_date), '%Y-%m-%d').strftime('%Y')
        from_date_month = datetime.strptime(str(self.from_date), '%Y-%m-%d').strftime('%m')
        to_date_month = datetime.strptime(str(self.to_date), '%Y-%m-%d').strftime('%m')
        if self.to_date < self.from_date:
            raise ValidationError(_('From date cannot be less than the to date.'))

        if from_date_year != to_date_year:
            raise ValidationError(_('Validity from date and to date must be of the year.'))

        if from_date_year == to_date_year:
            if from_date_month != to_date_month:
                raise ValidationError(_('Validity from date and to date must be of same the month.'))

    @api.model
    def _get_work_loc(self):
        if self.env.user.user_work_location_id:
            return self.env.user.user_work_location_id.id

    def probationary_employee_report_excel(self):
        from_date = self.from_date
        to_date = self.to_date
        department_id = self.department_id
        department_name = department_id.display_name if department_id else 'All'

        user_work_location_id = self.user_work_location_id
        user_work_location_name = self.user_work_location_id.display_name

        # get data from sql
        data = self.probationary_employee_report_sql(from_date, to_date, department_id, user_work_location_id)
        # print(data)

        from_date = datetime.strptime(str(from_date), '%Y-%m-%d').strftime('%d-%b-%Y')
        to_date = datetime.strptime(str(to_date), '%Y-%m-%d').strftime('%d-%b-%Y')

        file_name = "Probationary Employee Report (%s - %s).xlsx" % (data['form']['from_date'], data['form']['to_date'])
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

        sheet = workbook.add_worksheet('Probationary Employee Report')

        sheet.merge_range(0, 0, 0, 9, "Probationary Employee Report", format0)
        sheet.merge_range(1, 0, 1, 9, "Period: {0} to {1}".format(from_date, to_date), format0)
        sheet.merge_range(3, 0, 3, 2, 'Work/Job Location: {0}'.format(user_work_location_name) if user_work_location_name else "Work/Job Location: All", format1)
        sheet.merge_range(3, 3, 3, 5, 'Department Name: {0}'.format(department_name), format1)
        sheet.merge_range(3, 6, 3, 7, 'Office/Buisness Unit: {0}'.format(self.sbu_unit_id.display_name) if self.sbu_unit_id else "Office/Buisness Unit: All", format1)
        sheet.merge_range(3, 8, 3, 9, 'Tags: {0}'.format(','.join(self.category_ids.mapped('display_name'))) if self.sbu_unit_id else "Tags: No Tags Selected", format1)

        sheet.write(4, 0, 'Employee Name', format1)
        sheet.write(4, 1, 'Employee ID No', format1)
        sheet.write(4, 2, 'Work/Job Location', format1)
        sheet.write(4, 3, 'Department', format1)
        sheet.write(4, 4, 'Designation', format2)
        sheet.write(4, 5, 'Date of Joining', format2)
        sheet.write(4, 6, 'Probation Period', format2)
        sheet.write(4, 7, 'Date of Confirmation', format2)
        sheet.write(4, 8, 'Length of Service', format2)
        sheet.write(4, 9, 'Remaining Confirmation Date', format2)

        row = 5
        col = 0

        for rec in data['csr']:
            sheet.write(row, col, rec['employee_name'], format4)
            sheet.write(row, col + 1, rec['emp_id_card'], format4)
            sheet.write(row, col + 2, rec['work_location'], format4)
            sheet.write(row, col + 3, rec['department_name'], format4)
            sheet.write(row, col + 4, rec['designation_name'], format5)
            sheet.write(row, col + 5, str(rec['joining_date']), format5)
            sheet.write(row, col + 6, rec['probation'], format5)
            sheet.write(row, col + 7, str(rec['date_of_confirmation']), format5)
            sheet.write(row, col + 8, rec['length_of_service'], format5)
            sheet.write(row, col + 9, rec['remaining_confirmation_day'], format5)

            row = row + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Probationary Employee Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=probationary.employee.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def probationary_employee_report_pdf(self):
        from_date = self.from_date
        to_date = self.to_date
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.probationary_employee_report_sql(from_date, to_date, department_id, user_work_location_id)

        return self.env.ref(
            'custom_hr_report.probationary_employee_report_tmpl').with_context(landscape=True).report_action(self, data=data)

    def probationary_employee_report_sql(self, from_date, to_date, department_id, user_work_location_id):
        # m = int(month)
        # y = int(year)
        # ndays = monthrange(y, m)[1]
        # start_date = date(y, m, 1)
        # end_date = date(y, m, ndays)

        dept_filter = ""
        work_loc_filter = ""
        dept_name = "All"
        work_location_name = "All"
        tags_filter = ""
        business_unit_filter = ""   
        tag_filter_join = "LEFT"
        order_by = "main_tbl.employee_name"

        # order_by check
        order_by_flag = self.env['custom.common.settings'].search([('key', '=', 'hr_reports_order_by_employee_id')], limit=1)

        if order_by_flag.value:
            order_by = "main_tbl.emp_id_card"
        # print(order_by)

        if department_id:
            dept_filter = "AND he.department_id = %s" % department_id.id
            dept_name = department_id.display_name

        if user_work_location_id:
            work_loc_filter = "AND he.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids)>1:
                tags_filter = "WHERE etag.id IN {0}".format(tuple(self.category_ids.ids)) 

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])   


        if self.sbu_unit_id:
            business_unit_filter = "AND he.sbu_unit_id = {0}".format(self.sbu_unit_id.id) 

        data_sql = """
                    SELECT main_tbl.emp_id, main_tbl.employee_name, main_tbl.emp_id_card, sl.name AS work_location, hd.name->>'en_US' AS department_name, hj.name->>'en_US' AS designation_name, 
                    main_tbl.joining_date,hpp.name AS probation, main_tbl.date_of_confirmation
                    FROM (
							SELECT he.id AS emp_id, he.name AS employee_name, he.id_card_no AS emp_id_card, he.department_id AS dept_id, he.job_id AS des_id,
							he.user_work_location_id AS work_loc_id,he.initial_employment_date AS joining_date,he.probation_period AS probation_period,he.date_of_confirmation AS date_of_confirmation 
							FROM hr_employee he
							JOIN hr_contract hc ON hc.employee_id = he.id
                            {6} JOIN (
                                    SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                                    JOIN hr_employee_category etag on etag.id=ecr.category_id
                                    {5}
                                    GROUP BY emp_id
                                ) emp_tag ON emp_tag.emp_id = he.id
							WHERE he.employee_type_id = 2 AND he.active = true AND DATE(he.initial_employment_date) BETWEEN '{0}' AND '{1}' {2} {3} {4}
							ORDER BY he.name
                    ) main_tbl
                    LEFT JOIN hr_department hd on hd.id = main_tbl.dept_id
                    LEFT JOIN hr_job hj ON hj.id = main_tbl.des_id
                    LEFT JOIN stock_location sl ON sl.id = main_tbl.work_loc_id
					LEFT JOIN hr_probation_period hpp ON hpp.id = main_tbl.probation_period
                    ORDER BY {7}
                    """.format(from_date, to_date,
                                dept_filter, work_loc_filter,
                                business_unit_filter, tags_filter,
                                tag_filter_join, order_by)

        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()
        data_list = []

        for d in data_res:
            length_domain = self.env['hr.employee'].search(
                [('id', '=', d['emp_id'])])
            vals = {
                'employee_name': d['employee_name'],
                'emp_id_card': d['emp_id_card'],
                'work_location': d['work_location'],
                'department_name': d['department_name'],
                'designation_name': d['designation_name'],
                'joining_date': d['joining_date'],
                'probation': d['probation'],
                'date_of_confirmation': d['date_of_confirmation'],
                'length_of_service': length_domain.length_of_service,
                'remaining_confirmation_day': length_domain.remaining_confirmation_day,
            }
            data_list.append(vals)
        data = {
            'model': "employee.length.of.service.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'work_location_name': work_location_name if work_location_name else "All",
            'department_name': dept_name if dept_name else "All",
            'buisness_unit' : self.sbu_unit_id.display_name,
            'tag_names_list': ','.join(self.category_ids.mapped('display_name')),
        }
        return data

