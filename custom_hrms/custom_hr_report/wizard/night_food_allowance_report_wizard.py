from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
#import datetime
from datetime import datetime, timedelta
from itertools import groupby

import xlsxwriter

import base64
from io import BytesIO

class NightFoodAllowanceReportWizard(models.TransientModel):
    _name = "night.food.allowance.report.wizard"
    _description = "Tiffin Bill Allowance Report Wizard"

    file_data = fields.Binary('Night Food Allowance Report Wizard')
    start_date = fields.Date(string='From Date', default=fields.Date.today())
    end_date = fields.Date(string='To Date', default=fields.Date.today())
    #department_id = fields.Many2one('hr.department', string='Department')
    department_ids = fields.Many2many('hr.department', string='Department/Section')

    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', default=lambda self: self._get_work_loc(), domain=lambda self: self._set_domain_work_loc())

    based_on = fields.Selection([
        ('1', 'Eligible Hour After'),
        ('2', 'Touch Time After')
    ], string='Based On', default='1')
    eligible_hour = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
    ], string='Eligible Hour', default='3')
    touch_time_after = fields.Selection([
        ('8', '08:00'),
        ('9', '09:00'),
        ('10', '10:00'),
        ('11', '11:00'),
        ('12', '12:00'),
        ('13', '13:00'),
        ('14', '14:00'),
        ('15', '15:00'),
        ('16', '16:00'),
        ('17', '17:00'),
        ('18', '18:00'),
        ('19', '19:00'),
        ('20', '20:00'),
        ('21', '21:00'),
        ('22', '22:00'),
        ('23', '23:00'),
    ], string='Touch Time After')


    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('End date cannot be greater than the start date.'))

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

    def night_food_allowance_report_pdf(self):
        # start_date = self.start_date
        # end_date = self.end_date
        # touch_time_after = self.touch_time_after
        # department_ids = self.department_ids
        # work_location_id = self.user_work_location_id

        # get data from sql
        #data = self.night_food_allowance_report_sql(start_date, end_date, touch_time_after, department_ids, work_location_id)
        data = {'ftr_id': self.id}

        based_on = self.based_on
        if based_on == '1':
            return self.env.ref('custom_hr_report.tiffin_bill_report_id').with_context(landscape=False).report_action(self, data=data)
        else:
            return self.env.ref('custom_hr_report.night_food_allowance_report_id').with_context(landscape=False).report_action(self, data=data)

    def night_food_allowance_report_excel(self):
        start_date = self.start_date
        end_date = self.end_date
        touch_time_after = self.touch_time_after
        department_ids = self.department_ids
        user_work_location_id = self.user_work_location_id
        company_id = self.company_id

        based_on = self.based_on
        eligible_hour = self.eligible_hour
        touch_time_after = self.touch_time_after
        if based_on == '2':
            # get data from sql
            data = self.night_food_allowance_report_sql()

            start_date = datetime.strptime(str(start_date), '%Y-%m-%d').strftime('%d-%b-%Y')
            end_date = datetime.strptime(str(end_date), '%Y-%m-%d').strftime('%d-%b-%Y')

            file_name = "Night Food Allowance Report.xlsx"
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
                    sheet = workbook.add_worksheet(line[line2][0]['location_name'])

                    sheet.merge_range(0, 0, 0, 5, "{0}".format(data['form']['company_id'][1]), format0)
                    sheet.merge_range(1, 0, 2, 5,"Night Food Allowance Report",format0)

                    sheet.merge_range(3, 0, 3, 5, "Work/Job Location: %s" % data['work_loc_name'], format1)
                    sheet.merge_range(4, 0, 4, 5, "Department/Section: %s" % data['dept_name'], format1)
                    sheet.merge_range(5, 0, 5, 5, "Touch Time After: {0}".format(data['touch_time_after']), format2)

                    sheet.merge_range(6, 0, 6, 1, 'From Date: {0}'.format(start_date), format1)
                    sheet.merge_range(6, 3, 6, 5, 'To Date: {0}'.format(end_date), format3)

                    sheet.write(7, 0, 'Date', format2)
                    sheet.write(7, 1, 'Employee ID', format2)
                    sheet.write(7, 2, 'Name of Employee', format1)
                    sheet.write(7, 3, 'Punch Time', format1)
                    sheet.write(7, 4, 'Department', format1)
                    sheet.write(7, 5, 'Designation', format1)

                    row = 8
                    col = 0

                    for line3 in line[line2]:
                        sheet.write(row, col, datetime.strptime(str(line3['date']), '%Y-%m-%d').strftime('%d-%b-%Y'),
                                    format5)
                        sheet.write(row, col + 1, line3['emp_id_card'], format5)
                        sheet.write(row, col + 2, line3['employee_name'], format4)
                        sheet.write(row, col + 3, str(line3['timestamp2']), format4)
                        sheet.write(row, col + 4, line3['department_name'], format4)
                        sheet.write(row, col + 5, line3['designation_name'], format4)

                        row = row + 1

            workbook.close()
            file_pointer.seek(0)
            file_data = base64.b64encode(file_pointer.read())
            self.write({'file_data': file_data})
            file_pointer.close()

            return {
                'name': 'Night Food Allowance Report',
                'type': 'ir.actions.act_url',
                'url': '/web/content?model=night.food.allowance.report.wizard&field=file_data&id=%s&filename=%s' % (
                    self.id, file_name),
                'target': 'self',
            }
        else:
            # get data from sql
            data = self.night_food_allowance_report_sql()

            start_date = datetime.strptime(str(start_date), '%Y-%m-%d').strftime('%d-%b-%Y')
            end_date = datetime.strptime(str(end_date), '%Y-%m-%d').strftime('%d-%b-%Y')

            file_name = "Tiffin Bill Report.xlsx"
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
            #sheet.merge_range(0, 0, 0, 4, "{0}".format(data['form']['company_id'][1]), format0)
            sheet.merge_range(0, 0, 1, 7, "%s" % company_id.name, format0)
            sheet.merge_range(2, 0, 2, 7, "Work/Job Location: %s" % data['work_loc_name'], format1)
            sheet.merge_range(3, 0, 3, 7, "Department/Section: %s" % data['dept_name'], format1)
            sheet.merge_range(4, 0, 4, 4, "From Date: %s" % data['start_date'], format1)
            sheet.merge_range(4, 5, 4, 7, "To Date: %s" % data['end_date'], format1)
            sheet.merge_range(5, 0, 5, 7, "Eligible Hour: %s" % data['eligible_hour'], format1)

            sheet.merge_range(6, 0, 6, 7, "Tiffin Bill Report", format0)

            row =6
            # row = 5
            col = 0

            total_sl_no = 0
            for line in data['csr']:
                sl_no = 0
                for line2 in line:
                    if row > 5 and sl_no > 0:
                        sheet.merge_range(row, 0, row, 7, "Sub-Total: %s" % (sl_no), format1)
                        total_sl_no += sl_no
                    #-----------------
                    row = row + 1
                    sheet.merge_range(row, 0, row, 7,
                                      'Department/Section: {0}'.format(line[line2][0]['department_name']), format1)

                    row = row + 1

                    #sheet = workbook.add_worksheet(line[line2][0]['department_name'])

                    sheet.write(row, 0, 'SL', format2)
                    sheet.write(row, 1, 'Date', format2)
                    sheet.write(row, 2, 'Employee ID', format2)
                    sheet.write(row, 3, 'Name of Employee', format1)
                    sheet.write(row, 4, 'Category', format1)
                    sheet.write(row, 5, 'Designation', format1)
                    sheet.write(row, 6, 'Shift', format1)
                    sheet.write(row, 7, 'Out Time', format1)

                    row +=1
                    sl_no = 0
                    for line3 in line[line2]:
                        sl_no += 1
                        sheet.write(row, col, sl_no, format5)
                        col = col + 1
                        sheet.write(row, col, datetime.strptime(str(line3['date']), '%Y-%m-%d').strftime('%d-%b-%Y'), format5)
                        col = col + 1
                        sheet.write(row, col, line3['emp_id_card'], format5)
                        col = col + 1
                        sheet.write(row, col, line3['employee_name'], format4)
                        col = col + 1
                        sheet.write(row, col, line3['emp_category'], format4)
                        col = col + 1
                        sheet.write(row, col, line3['designation_name'], format4)
                        col = col + 1
                        sheet.write(row, col, line3['emp_shift'], format4)
                        col = col + 1

                        out_time = self._get_time_from_float(line3['date'],line3['check_out_time'])

                        sheet.write(row, col, out_time, format4)

                        row = row + 1
                        col = 0

                if sl_no > 0:
                    sheet.merge_range(row, 0, row, 7, "Sub-Total: %s" % (sl_no), format1)
                    total_sl_no += sl_no

            row = row + 1
            sheet.merge_range(row, 0, row, 7, "Grand-Total: %s" % (total_sl_no), format1)

            workbook.close()
            file_pointer.seek(0)
            file_data = base64.b64encode(file_pointer.read())
            self.write({'file_data': file_data})
            file_pointer.close()

            return {
                'name': 'Tiffin Bill Report',
                'type': 'ir.actions.act_url',
                'url': '/web/content?model=night.food.allowance.report.wizard&field=file_data&id=%s&filename=%s' % (
                    self.id, file_name),
                'target': 'self',
            }


    def night_food_allowance_report_sql(self):
        dept_filter = ""
        work_loc_filter = ""
        dept_name = "All"
        work_location_name = "All"

        start_date = self.start_date
        end_date = self.end_date
        user_work_location_id = self.user_work_location_id
        department_ids = self.department_ids

        based_on = self.based_on
        eligible_hour = self.eligible_hour
        touch_time_after = self.touch_time_after


        # if department_id:
        #     dept_filter = "AND hr.department_id = %s" % department_id.id
        #     dept_name = department_id.display_name

        if len(department_ids) > 1:
            dept_filter = "AND hr.department_id in {0}".format(tuple(department_ids.ids))
            dept_name = ", ".join([d.name for d in department_ids])
        elif len(department_ids) == 1:
            dept_filter = "AND hr.department_id = %s" % department_ids.id
            dept_name = department_ids.name

        if user_work_location_id:
            work_loc_filter = "AND hr.user_work_location_id = %s" % user_work_location_id.id
            work_location_name = user_work_location_id.display_name

        data_sql = ""
        if based_on=='1':
            data_sql = """
                    SELECT easl.date AS date, hr.id_card_no AS emp_id_card, hr.name AS employee_name, easl.overtime AS overtime_hours_time, easl.ac_sign_in AS check_in_time, easl.ac_sign_out AS check_out_time,
                    hd.id AS department_id,hd.name->>'en_US' AS department_name, hj.name->>'en_US' AS designation_name, COALESCE(hr.user_work_location_id, 100000) AS user_work_location_id, sl.name AS location_name,hct.name AS emp_category,rcal.short_name AS emp_shift
                    FROM employee_attendance_sheet_line easl
                    JOIN hr_employee hr ON hr.id = easl.employee_id                    
                    JOIN hr_department hd ON hd.id = hr.department_id
                    JOIN stock_location sl ON sl.id = hr.user_work_location_id
                    LEFT JOIN hr_job hj ON hj.id = hr.job_id
                    LEFT JOIN hr_contract hc ON hc.id = hr.contract_id
                    LEFT JOIN hr_contract_type hct ON hct.id = hc.contract_type_id
                    LEFT JOIN resource_calendar rcal ON rcal.id = hc.resource_calendar_id
                    WHERE DATE(easl.date) BETWEEN '{0}' AND '{1}' {2} {3} AND easl.overtime >= {4} AND easl.ovt_flag = '1'
                    ORDER BY hd.name, easl.date, hr.id_card_no
                    """.format(start_date, end_date, dept_filter, work_loc_filter, eligible_hour)

        elif based_on=='2':
            data_sql = """
                    SELECT DATE(ua.timestamp) AS date, hr.id_card_no AS emp_id_card, hr.name AS employee_name,ua.timestamp as timestamp, (ua.timestamp + interval '6 hours') as timestamp2, hd.id AS department_id, hd.name->>'en_US' AS department_name, hj.name->>'en_US' AS designation_name, COALESCE(hr.user_work_location_id, 100000) AS user_work_location_id, sl.name AS location_name
                    FROM user_attendance ua
                    JOIN hr_employee hr ON hr.id = ua.employee_id
                    LEFT JOIN hr_job hj ON hj.id = hr.job_id
                    LEFT JOIN stock_location sl ON sl.id = hr.user_work_location_id
                    LEFT JOIN hr_department hd ON hd.id = hr.department_id
                    WHERE ua.valid='True' AND (EXTRACT(hour from ua.timestamp) + 6) = {0} AND DATE(ua.timestamp) BETWEEN '{1}' AND '{2}' {3} {4}
                    GROUP BY DATE(ua.timestamp), hr.name, hj.name, hr.id_card_no, hd.name, hr.user_work_location_id, sl.name, ua.timestamp, hd.id
                    ORDER BY hr.user_work_location_id, hr.id_card_no, DATE(ua.timestamp)
                    """.format(touch_time_after, start_date, end_date, dept_filter, work_loc_filter)


        self.env.cr.execute(data_sql)
        data_list = self.env.cr.dictfetchall()

        # define a fuction for key
        def key_func(k):
            if based_on == '1':
                return k['department_id']
            else:
                return k['location_name']

        data_list = sorted(data_list, key=key_func)

        final_data_list = []

        for key, value in groupby(data_list, key_func):
            vals = {
                key: list(value)
            }
            final_data_list.append(vals)

        data = {
            'model': "night.food.allowance.report.wizard",
            'form': self.read()[0],
            'csr': final_data_list,
            'touch_time_after': dict(self._fields['touch_time_after'].selection).get(self.touch_time_after),
            'work_loc_name': work_location_name,
            'dept_name': dept_name,
            'start_date': start_date,
            'end_date': end_date,
            'eligible_hour': eligible_hour
        }
        return data

    def _get_time_from_float(self, date, float_time):
        time2 = str(timedelta(hours=float_time)).rsplit(':', 1)[0]

        out_time = datetime.strptime(str(date) + ' ' + str(time2), '%Y-%m-%d %H:%M') + timedelta(hours=6) if time2 else ''
        out_time2 = out_time.strftime('%H:%M') if out_time else ''

        return out_time2


