import datetime

from odoo import api, fields, models, _
from odoo.tools.misc import get_lang

from datetime import datetime, date, timedelta
from calendar import monthrange


def last_day_of_month(any_day):
    import datetime
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
    return next_month - datetime.timedelta(days=next_month.day)


def get_years():
    year_list = []
    crn_year = datetime.now().year
    for i in range(2021, crn_year + 5):
        year_list.append((str(i), str(i)))
    return year_list


class AttendanceReport(models.TransientModel):
    _name = 'evl.attendance.report'
    _description = 'Attendance Report'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    work_branch = fields.Many2one('stock.warehouse', string='Branch')
    work_section = fields.Many2one('stock.location', string='Section', domain=[('state', '=', 'done'), ('is_work_loc', '=', True)])
    employee_id = fields.Many2one(string='Employeee', comodel_name='hr.employee')
    company_currency_id = fields.Many2one('res.currency', readonly=True, default=lambda x: x.env.company.currency_id)
    absent_day = fields.Integer(string='Absent Day')
    joining_date = fields.Selection([
        ('all', 'All Date'),
        ('select', 'Selected Date')], string='Joining Date Selection',
        default='all')
    report_type = fields.Selection([
        ('month', 'Month Wise'),
        ('year', 'Year Selection'),
        ('date', 'Date Wise'),
        ('all', 'All'),
    ], string='Time Selection',
        default='month', help="Defines how a report will be generated(month-wise or date-wise)", required=True)
    month = fields.Selection(
        [('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
         ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
         ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December'), ],
        string='Month')
    year = fields.Selection(get_years(), string='Year')
    report_option = fields.Selection([
        ('details', 'Details'),
        ('summary', 'Summary'),
    ], string='Report Option', default='details')

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')

    def _build_contexts(self, data):
        from datetime import datetime
        branch = self.work_branch
        result = {}
        result['company_id'] = self.company_id
        pages = []
        pg_no = 1

        if self.report_type == 'month':
            m = int(self.month)
        if self.report_type in ('month', 'year'):
            y = int(self.year)
        ndays = monthrange(y, m)[1]
        from_date = date(y, m, 1)
        to_date = date(y, m, ndays)
        delta = to_date - from_date

        date_list = [(from_date + timedelta(days=i)) for i in range(delta.days + 1)]

        day_list = [i.day for i in date_list]

        # report_time = datetime.now()
        #
        # year = report_time.year if self.year == False else self.year
        # month = report_time.month if self.month == False else self.month

        if self.report_type == 'month':
            first_of_month = from_date
            last_of_month = to_date
        else:
            first_of_month = data['form']['date_from'] or False
            last_of_month = data['form']['date_to'] or False

        week_days = []

        for rec in date_list:
            if rec.weekday() == 0:
                week_days.append('M')
            elif rec.weekday() == 1:
                week_days.append('T')
            elif rec.weekday() == 2:
                week_days.append('W')
            elif rec.weekday() == 3:
                week_days.append('T')
            elif rec.weekday() == 4:
                week_days.append('F')
            elif rec.weekday() == 5:
                week_days.append('S')
            else:
                week_days.append('S')

        emp_query = """
                SELECT he.name as name , he.id_card_no as emp_id,
                ha.employee_id as em_id,
                json_object_agg(DISTINCT EXTRACT(DAY FROM em.date_time), concat(ha.remark,'*L*',ha.is_late,'*H*',ha.is_holiday,'*G*',ha.is_global_leave,'*P*',ha.paid_leave, '*F*',ha.manual_absent, '*C*',ha.leave_code, '*E*',ha.is_early, '*M*',ha.is_manual_att)) as day_data,
                
                COALESCE(atts.no_absence, 0) AS no_abs,
                COALESCE(atts.no_absence, 0) AS no_abs

                (SELECT COUNT(record_date) 
                FROM 
                    hr_attendance 
                WHERE 
                    (DATE(record_date) >= %s AND  DATE(record_date) <= %s
                AND employee_id = ha.employee_id)
                AND (remark not in ('Holiday','Holiday,Attendance')))
                as n_wday,

                (SELECT COUNT(record_date ) 
                FROM hr_attendance 
                WHERE (DATE(record_date) >= %s AND  DATE(record_date) <= %s
                AND employee_id = ha.employee_id)
                AND ( remark ='Movement' OR remark='Attendance' or remark='Movement,Attendance') )

                as ac_wday,
                (SELECT COUNT(record_date ) 
                FROM hr_attendance 
                WHERE (DATE(record_date) >= %s AND  DATE(record_date) <= %s
                AND employee_id = ha.employee_id)
                AND ( remark ='Absent' ) )  as ab_wday,

                (SELECT COUNT(record_date) 
                FROM hr_attendance 
                WHERE (DATE(record_date) >= %s AND  DATE(record_date) <= %s
                --AND late_time_daily > 0.00
                AND is_late = true
                AND employee_id = ha.employee_id))  as late_day,

                (SELECT COUNT(record_date) 
                FROM hr_attendance 
                WHERE (DATE(record_date) >= %s AND  DATE(record_date) <= %s
                --AND early_leave_time = ha.early_leave_time
                --AND early_leave_time > 0.00
                AND is_early = true
                AND employee_id = ha.employee_id))  as early_day,

                CAST(SUM(ea.early_leave_time)::Numeric AS INT)  as early_min,
                CAST(SUM(ea.late_time_daily)::Numeric As INT)   as late_min,
                '' as ot_hour,
                '' as week_ot,

                hj.name as designation,
                rc.name as company_name,
                sl.name sec_name

                FROM hr_attendance ha ON em.date_time = ha.record_date
                LEFT JOIN hr_employee he ON ha.employee_id=he.id
                LEFT JOIN attendance_sheet atts ON atts.employee_id=he.id
                LEFT JOIN stock_location sl ON he.work_section=sl.id
                LEFT JOIN hr_job hj ON he.job_id= hj.id
                LEFT JOIN res_company rc ON he.company_id= rc.id

                WHERE DATE(ha.attendance_date) BETWEEN %s AND %s AND he.active ='True'
        """

        company_id = self.env['res.company'].search([('id', '=', data['form']['company_id'][0])])
        work_branch = False
        work_section = False

        if data['form']['company_id'] != False:
            company_id = self.env['res.company'].search([('id', '=', data['form']['company_id'][0])])
            emp_query = emp_query + """AND he.company_id='%s'""" % company_id.id

            if data['form']['work_branch'] != False and data['form']['work_section'] == False:
                work_branch = self.env['stock.warehouse'].search([('id', '=', data['form']['work_branch'][0])])
                emp_query = emp_query + """ AND he.wh_location_id=%s""" % work_branch.id
            if data['form']['work_branch'] != False and data['form']['work_section'] != False:
                work_branch = self.env['stock.warehouse'].search([('id', '=', data['form']['work_branch'][0])])
                work_section = self.env['stock.location'].search([('id', '=', data['form']['work_section'][0])])
                emp_query = emp_query + """ AND he.wh_location_id=%s AND he.work_section=%s""" % (
                work_branch.id, work_section.id)
            if data['form']['work_branch'] == False and data['form']['work_section'] != False:
                work_section = self.env['stock.location'].search([('id', '=', data['form']['work_section'][0])])
                emp_query = emp_query + """ AND he.work_section=%s""" % (work_section.id)

            if data['form']['work_branch'] == False and data['form']['work_section'] == False and data['form'][
                'employee_id'] == False and data['form']['job_status'] == False:
                if data['form']['employee_id'] != False:
                    employee = self.env['hr.employee'].search([('id', '=', data['form']['employee_id'][0])])
                    emp_query = emp_query + """ AND he.id=%s""" % employee.id
            else:
                if data['form']['employee_id'] != False:
                    employee = self.env['hr.employee'].search([('id', '=', data['form']['employee_id'][0])])
                    emp_query = emp_query + """ AND he.id=%s""" % employee.id

        if data['form']['company_id'] == False:
            if data['form']['work_branch'] != False and data['form']['work_section'] == False:
                work_branch = self.env['stock.warehouse'].search([('id', '=', data['form']['work_branch'][0])])
                emp_query = emp_query + """AND he.wh_location_id=%s""" % work_branch.id
            if data['form']['work_branch'] != False and data['form']['work_section'] != False:
                work_branch = self.env['stock.warehouse'].search([('id', '=', data['form']['work_branch'][0])])
                work_section = self.env['stock.location'].search([('id', '=', data['form']['work_section'][0])])
                emp_query = emp_query + """AND he.wh_location_id=%s AND he.work_section=%s""" % (
                work_branch.id, work_section.id)
            if data['form']['work_branch'] == False and data['form']['work_section'] != False:
                work_section = self.env['stock.location'].search([('id', '=', data['form']['work_section'][0])])
                emp_query = emp_query + """AND he.work_section=%s""" % (work_section.id)
                # if data['form']['work_branch'] == False and  data['form']['work_section'] == False and data['form']['employee_id'] == False:
            #     if data['form']['job_status'] != False:
            #         emp_query = emp_query + """AND he.job_status='%s' """ %(data['form']['job_status'])

            # if data['form']['work_branch'] != False or  data['form']['work_section'] != False or data['form']['employee_id'] != False:
            #     if data['form']['job_status'] != False:
            #         emp_query = emp_query + """AND he.job_status='%s'""" %(data['form']['job_status'])

            if data['form']['work_branch'] == False and data['form']['work_section'] == False and data['form'][
                'employee_id'] == False and data['form']['job_status'] == False:
                if data['form']['employee_id'] != False:
                    employee = self.env['hr.employee'].search([('id', '=', data['form']['employee_id'][0])])
                    emp_query = emp_query + """AND he.id=%s""" % employee.id
            else:
                if data['form']['employee_id'] != False:
                    employee = self.env['hr.employee'].search([('id', '=', data['form']['employee_id'][0])])
                    emp_query = emp_query + """AND he.id=%s""" % employee.id

        # Not required
        # if data['form']['work_branch'] != False and data['form']['work_section'] == False:
        #     work_branch =  data['form']['work_branch'][0]
        #     body = body + """AND he.wh_location_id=%s""" %work_branch
        # if data['form']['work_branch'] != False and data['form']['work_section'] != False:
        #     body = body + """AND he.wh_location_id=%s AND he.work_section=%s""" %(data['form']['work_branch'][0],data['form']['work_section'][0])
        # if data['form']['work_branch'] == False  and data['form']['work_section'] != False:
        #     body = body + """AND he.work_section=%s""" %(data['form']['work_section'][0])

        emp_query = emp_query + """GROUP BY he.old_empid,ha.employee_id,he.name,hj.name,rc.name,sw.name,sl.name"""

        self._cr.execute(emp_query, (
        first_of_month, last_of_month, first_of_month, last_of_month, first_of_month, last_of_month, first_of_month,
        last_of_month, first_of_month, last_of_month, first_of_month, last_of_month))
        body = self._cr.dictfetchall()
        lon = 0

        for bd in body:
            lon = 1

            keys = []
            for key, value in bd['day_data'].items():
                lon += 1
                if value != None:
                    attn_value = value.split('*')
                    values = attn_value[0].split(",")

                    #   remark = attn_value[0], is_late = [2], is_holiday = [4], is_global_leave = [6], paid_leave = [8], manual_absent = [10],
                    #   leave_code = [12], is_early = [14], is_manual_att = [16]

                    if len(values) == 1:

                        if attn_value[0] == 'Attendance' and (attn_value[2] == 'f' or attn_value[2] == '') and (
                                attn_value[14] == 'f' or attn_value[2] == ''):
                            if attn_value[16] == 'f' or attn_value[16] == '':
                                bd['day_data'][key] = 'P'
                            elif attn_value[16] == 't':
                                bd['day_data'][key] = 'MP'

                        elif attn_value[0] == 'Movement':
                            bd['day_data'][key] = 'M'
                        elif attn_value[0] == 'Absent':
                            bd['day_data'][key] = 'A'
                        elif attn_value[0] == 'Suspend':
                            bd['day_data'][key] = 'U'
                        elif attn_value[0] == 'Leave':
                            bd['day_data'][key] = 'V'

                        elif attn_value[0] == 'Attendance' and attn_value[2] == 't' and (
                                attn_value[14] == 'f' or attn_value[14] == ''):
                            if attn_value[16] == 'f' or attn_value[16] == '':
                                bd['day_data'][key] = 'L'
                            elif attn_value[16] == 't':
                                bd['day_data'][key] = 'ML'

                        elif attn_value[0] == 'Attendance' and attn_value[14] == 't' and (
                                attn_value[2] == 'f' or attn_value[2] == ''):
                            if attn_value[16] == 'f' or attn_value[16] == '':
                                bd['day_data'][key] = 'E'
                            elif attn_value[16] == 't':
                                bd['day_data'][key] = 'ME'

                        elif attn_value[0] == 'Attendance' and attn_value[14] == 't' and attn_value[2] == 't':
                            if attn_value[16] == 'f' or attn_value[16] == '':
                                bd['day_data'][key] = 'LE'
                            elif attn_value[16] == 't':
                                bd['day_data'][key] = 'Z'

                        elif attn_value[12] == 'SL':
                            bd['day_data'][key] = 'S'
                        elif attn_value[8] == 't':
                            bd['day_data'][key] = 'WP'
                        # elif value == 'Leave without Application':
                        #     bd['day_data'][key] = 'LWA'
                        elif attn_value[0] == 'Holiday' and attn_value[6] == 't':
                            bd['day_data'][key] = 'H'
                        elif attn_value[0] == 'overtime':
                            bd['day_data'][key] = 'OT'
                        elif attn_value[0] == 'Holiday' and attn_value[4] == 't':
                            bd['day_data'][key] = 'W'
                        elif attn_value[0] == 'Earned Leave':
                            bd['day_data'][key] = 'EL'
                        elif attn_value[12] == 'CL':
                            bd['day_data'][key] = 'C'
                        elif attn_value[0] == 'On Duty':
                            bd['day_data'][key] = 'OD'
                        elif attn_value[0] == 'Day Off':
                            bd['day_data'][key] = 'DO'
                        elif attn_value[0] == 'Manual Attendance':
                            bd['day_data'][key] = 'M'
                        elif attn_value[10] == 't':
                            bd['day_data'][key] = 'F'
                        else:
                            bd['day_data'][key] = value[0]

                    if len(values) > 1:
                        if 'Attendance' in values and 'Movement' in values:
                            bd['day_data'][key] = 'K'
                        if 'Attendance' in values and 'Holiday' in values:
                            bd['day_data'][key] = 'O'
                        elif 'Attendance' in values and 'Leave' in values:
                            bd['day_data'][key] = 'X'
                keys.append(key)

            for i in range(first_of_month.day, last_of_month.day + 1):
                if str(i) not in keys:
                    bd['day_data'][str(i)] = 'A'

        lon = 2 + lon + 7

        # ---------------------------------------------------------------------------------

        companies = []
        branches = []
        sections = []

        row_lines = body
        for emp in row_lines:
            emp['company_name'] = 'N/A' if emp['company_name'] == None or False else emp['company_name']
            emp['br_name'] = 'N/A' if emp['br_name'] == None or False else emp['br_name']
            emp['sec_name'] = 'N/A' if emp['sec_name'] == None or False else emp['sec_name']

            if emp['company_name'] not in companies:
                companies.append(emp['company_name'] if emp['company_name'] != None else 'N/A')
            if emp['br_name'] not in branches:
                branches.append(emp['br_name'] if emp['br_name'] != None else 'N/A')
            if emp['sec_name'] not in sections:
                sections.append(emp['sec_name'] if emp['sec_name'] != None else 'N/A')

        coms = []
        coms.append({'company_name': '', 'br_name': '', 'sec_name': ''})

        for com in companies:
            for br in branches:
                for sec in sections:
                    for cum in coms:

                        if com not in cum['company_name'] and br not in cum['br_name'] and sec not in cum['sec_name']:
                            coms.append({'company_name': com, 'br_name': br, 'sec_name': sec})

        del (coms[0])

        for com in coms:
            rows = []
            for em in row_lines:
                if em['company_name'] == com['company_name'] and em['br_name'] == com['br_name'] and em['sec_name'] == \
                        com['sec_name']:
                    rows.append(em)
                com['row_lines'] = rows

        # #---------------------------------------------------------------------------

        row_lines = []
        pg_toto = pg_no = 1
        footers = {
            'print_date': report_time,
            'pg_no': pg_no,
            'pg_toto': pg_toto
        }

        result = {}
        result['head_r'] = head_r
        result['heads2_r'] = heads2_r
        headers = {}
        company_id = self.env['res.company'].search([('id', '=', data['form']['company_id'][0])])
        headers['company_name'] = company_id.name if len(company_id) > 0 else False
        headers['br_name'] = work_branch.name if work_branch != False else False
        headers['sec_name'] = work_section.name if work_section != False else False
        headers['month'] = dict(self._fields['month'].selection).get(self.month)
        headers['year'] = dict(self._fields['year'].selection).get(self.year)

        headers['street'] = company_id.street if len(company_id) > 0 else False
        headers['street2'] = company_id.street2 if len(company_id) > 0 else False
        headers['city'] = company_id.city if len(company_id) > 0 else False
        headers['country'] = company_id.country_id.name if len(company_id) > 0 else False
        result['headers'] = headers
        result['company_id'] = company_id
        result['body'] = body
        result['coms'] = coms
        result['footers'] = {'date_time': report_time, 'lon': lon}
        pages.append({'coms': coms, 'footers': result['footers'], 'headers': headers})
        result['pages'] = pages
        return result

    def _print_report(self, data):
        raise NotImplementedError()

    def print_preview(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('hr.employee')
        data['form'] = self.read()[0]
        rows = self._build_contexts(data)
        companyid = self.work_branch.company_id
        data['pages'] = rows['pages']
        data['footers'] = rows['footers']
        data['header'] = rows['head_r']
        data['heads2_r'] = rows['heads2_r']
        data['body'] = rows['body']
        data['headers'] = rows['headers']
        data['phone'] = companyid.phone
        data['coms'] = rows['coms']

        company_id = self.env['res.company'].search([('id', '=', data['form']['company_id'][0])])

        test_company = {}
        test_company['id'] = company_id.id
        test_company['logo'] = company_id.logo
        test_company['name'] = company_id.name
        test_company['street'] = company_id.street
        external_report_layout_id = {}
        external_report_layout_id['key'] = company_id.external_report_layout_id.key
        test_company['external_report_layout_id'] = external_report_layout_id
        test_company['partner_id'] = company_id.partner_id.id
        test_company['report_header'] = company_id.report_header
        data['test_company'] = test_company

        # return self.env.ref('evl_hr_reports.report_attendance_list').report_action(self, data=data)

        # data = self.prepare_data()
        return self.env.ref('custom_hr_employee.attendance_preview').report_action(self, data=data)

    def print_attendance_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('hr.employee')
        data['form'] = self.read()[0]
        rows = self._build_contexts(data)
        companyid = self.work_branch.company_id
        data['pages'] = rows['pages']
        data['footers'] = rows['footers']
        data['header'] = rows['head_r']
        data['heads2_r'] = rows['heads2_r']
        data['body'] = rows['body']
        data['headers'] = rows['headers']
        data['phone'] = companyid.phone
        data['coms'] = rows['coms']

        company_id = self.env['res.company'].search([('id', '=', data['form']['company_id'][0])])

        test_company = {}
        test_company['id'] = company_id.id
        test_company['logo'] = company_id.logo
        test_company['name'] = company_id.name
        test_company['street'] = company_id.street
        external_report_layout_id = {}
        external_report_layout_id['key'] = company_id.external_report_layout_id.key
        test_company['external_report_layout_id'] = external_report_layout_id
        test_company['partner_id'] = company_id.partner_id.id
        test_company['report_header'] = company_id.report_header
        data['test_company'] = test_company

        return self.env.ref('custom_hr_employee.report_attendance_list').report_action(self, data=data)