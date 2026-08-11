import pytz
import math
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date
from calendar import monthrange

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT = "%H:%M:%S"


class AttendanceSheet(models.Model):
    _name = 'attendance.sheet'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _description = 'Hr Attendance Sheet'
    _order = "id desc"

    name = fields.Char("Name")
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', index=True,
                                  required=True)
    id_card_no = fields.Char(string="Employee ID", groups="hr.group_hr_user",
                             related='employee_id.id_card_no')

    manual_reason = fields.Many2one('hr.attendance', string='reason')

    department_id = fields.Many2one(related='employee_id.department_id',
                                    string='Department')
    initial_employment_date = fields.Date(related='employee_id.initial_employment_date', string='Date of Joining')
    is_separated = fields.Boolean(string="Is Separated?", related='employee_id.is_separated')
    separation_date = fields.Date('Separation Date', related='employee_id.separation_date')

    job_id = fields.Many2one('hr.job', string="Designation", related="employee_id.job_id")
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 copy=False, required=True,
                                 default=lambda self: self.env.company)
                                 # states={'draft': [('readonly', False)]})
    date_from = fields.Date(string='Date From', readonly=True, required=True, index=True,
                            default=lambda self: fields.Date.to_string(
                                date.today().replace(day=1) - relativedelta(months=1)))
    date_to = fields.Date(string='Date To', readonly=True, required=True, index=True, default=lambda self: fields.Date.to_string(((date.today().replace(day=1) - relativedelta(months=1)) + relativedelta(months=+1, day=1,days=-1))))
    line_ids = fields.One2many(comodel_name='attendance.sheet.line',
                               string='Attendances', readonly=True,
                               inverse_name='att_sheet_id')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Approved'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True,
        string='Status', required=True, readonly=True, index=True,
        help=' * The \'Draft\' status is used when a HR user is creating a new  attendance sheet. '
             '\n* The \'Confirmed\' status is used when  attendance sheet is confirmed by HR user.'
             '\n* The \'Approved\' status is used when  attendance sheet is accepted by the HR Manager.')
    no_overtime = fields.Integer(compute="_compute_sheet_total",
                                 string="No. of Overtimes", readonly=True,
                                 store=True)
    tot_overtime = fields.Float(compute="_compute_sheet_total",
                                string="Total Overtime", readonly=True,
                                store=True)
    tot_difftime = fields.Float(compute="_compute_sheet_total",
                                string="Total Diff time Hours", readonly=True,
                                store=True)
    no_difftime = fields.Integer(compute="_compute_sheet_total",
                                 string="No. of Diff Times", readonly=True,
                                 store=True)
    tot_late = fields.Float(compute="_compute_sheet_total",
                            string="Total Late In Hours", readonly=True, store=True)
    tot_late_abs = fields.Float(compute="_compute_sheet_total",
                            string="Total Late In Absent Hours", readonly=True, store=True)

    no_late = fields.Integer(compute="_compute_sheet_total",
                             string="Total Late Days",
                             readonly=True, store=True)
    no_late_abs = fields.Integer(compute="_compute_sheet_total",
                             string="Total Absent Late Days",
                             readonly=True, store=True)

    no_absence = fields.Integer(compute="_compute_sheet_total",
                                string="No. of Absence Days", readonly=True,
                                store=True)

    no_join_resign_ded_count = fields.Integer(compute="_compute_sheet_total",
                                string="Join/Resign Deduction Days", readonly=True,
                                store=True)

    tot_absence = fields.Float(compute="_compute_sheet_total",
                               string="Total Absence Hours", readonly=True,
                               store=True)
    tot_worked_hour = fields.Float(compute="_compute_sheet_total",
                                   string="Total Late In", readonly=True,
                                   store=True)
    no_presence = fields.Integer(compute="_compute_sheet_total",
                                 string="No. of Presence", readonly=True,
                                 store=True)
    tot_presence = fields.Float(compute="_compute_sheet_total",
                               string="Total Presence Hours", readonly=True,
                               store=True)
    no_leave = fields.Integer(compute="_compute_sheet_total",
                              string="No. of Leave", readonly=True, default=0,
                              store=True)
    no_cl = fields.Integer(compute="_compute_sheet_total",
                            string="No. of CL", readonly=True, default=0, store=True)
    no_ml = fields.Integer(compute="_compute_sheet_total",
                            string="No. of ML", readonly=True, default=0, store=True)
    no_pl = fields.Integer(compute="_compute_sheet_total",
                           string="No. of PL/EL", readonly=True, default=0, store=True, help="Paid Leave or Privilege Leave or Earn Leave")
    no_lwp = fields.Integer(compute="_compute_sheet_total",
                            string="No. of LWP", readonly=True, default=0, store=True)
    no_weekend = fields.Integer(compute="_compute_sheet_total",
                                string="No. of Weekend", readonly=True, default=0,
                                store=True)
    no_ph = fields.Integer(compute="_compute_sheet_total",
                           string="No. of Public Holiday", readonly=True, default=0,
                           store=True)
    # no_leave = fields.Integer(compute="_compute_sheet_total",
    #                              string="No of Leave", readonly=True,
    #                              store=True)
    att_policy_id = fields.Many2one(comodel_name='hr.attendance.policy',
                                    string="Attendance Policy ", required=True)
    payslip_id = fields.Many2one(comodel_name='hr.payslip', string='Payslip')
    payslip_state = fields.Selection(string='Payslip Status', related='payslip_id.state')

    contract_id = fields.Many2one('hr.contract', string='Contract',
                                  readonly=True)
                                  # states={'draft': [('readonly', False)]})
    gross_salary = fields.Float(string="Gross Salary", digits=(16, 2))
    basic_salary = fields.Float(string="Basic Salary", digits=(16, 2), help="Apply on ML deduction.")
    no_of_calendar_days = fields.Integer(string="No. of Calendar Days", help="Based on End date's month. apply on Extra allowance and ML deduction")
    no_of_days = fields.Integer(string="No. of Working Days", help="Based on Date range and policy flag. apply on Per day salary, OT, daily tiffin allowance.")
    no_of_total_days = fields.Integer(string="No. of Total Days (Date-Range)", help="Based on Date range. differance between two dates and using for working days, join/rejoin.")

    per_day_salary = fields.Float(string="Per Day Salary", digits=(16, 2))
    # per_day_salary_max = fields.Float(string="Per Day Salary (Max)", digits=(16, 2), help="Based on Gross and Total Days")

    actual_late_count = fields.Integer(string="Late Count For Deduction", readonly=True, store=True)

    actual_diff_count = fields.Integer(string="Actual Early Out Count", readonly=True, store=True)
    actual_abs_count = fields.Integer(string="Actual Absence Count", readonly=True, store=True)
    actual_abs_count_late = fields.Float(string="Absent Count For Late", readonly=True, store=True)

    ot_day_count = fields.Float(string="Actual Overtime Day Count", help="Overtime Day Count")
    ot_daily_allowance = fields.Float(string="Daily Overtime Allowance", help="Daily Overtime Allowance")
    ot_daily_salary = fields.Float(string="Daily Overtime Salary", help="Daily Overtime Salary")

    no_att_bonus = fields.Integer(string="No. of Att. Bonus", default=0, help="No. of Attendance Bonus", compute="_compute_sheet_total", store=True)
    no_extra_allowance = fields.Integer(string="No. of Extra Allowance", default=0, help="No. of Extra Allowance")

    batch_att_sheet_id = fields.Many2one('batch.attendance.sheet', string='Batch Attendance Sheet', readonly=True,
                                         copy=False,
                                         # states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                         ondelete='cascade',
                                         domain="[('company_id', '=', company_id)]")

    def unlink(self):
        for rec in self:
            if any(rec.filtered(lambda rec: rec.state not in ('draft'))):
                raise UserError(_(
                    'You cannot delete an attendance sheet which is confirmed or approved!'))
        return super(AttendanceSheet, self).unlink()

    @api.constrains('date_from', 'date_to')
    def check_date(self):
        for sheet in self:
            emp_sheets = self.env['attendance.sheet'].search(
                [('employee_id', '=', sheet.employee_id.id), ('id', '!=', sheet.id), ('state', '!=', 'cancel')])
            for emp_sheet in emp_sheets:
                if max(sheet.date_from, emp_sheet.date_from) < min(sheet.date_to, emp_sheet.date_to):
                    raise UserError(
                        _("Employee '%s' attendance Sheet already generated during this period. Please pick another date!" % (
                            emp_sheet.employee_id.name)))

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def action_approve(self):
        self.action_create_payslip()
        self.write({'state': 'done'})

    def action_payslip_done(self):
        for rec in self:
            if rec.payslip_id:
                if rec.payslip_id.state != 'done':
                    rec.payslip_id.action_payslip_done()


    def action_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        for rec in self:
            rec.payslip_id.action_payslip_cancel()
            rec.state = 'cancel'

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        self.name = 'Attendance Sheet - %s - %s' % (self.employee_id.name or '',
                                                    format_date(self.env,
                                                                self.date_to,
                                                                date_format="MMMM y"))
        self.user_work_location_id = employee.user_work_location_id
        self.company_id = employee.company_id
        contracts = employee._get_contracts(date_from, date_to)
        if not contracts:
            raise ValidationError(
                _('There Is No Valid Contract For Employee %s' % employee.name))
        self.contract_id = contracts[0]
        if not self.contract_id.att_policy_id:
            raise ValidationError(_(
                "Employee %s does not have attendance policy" % employee.name))
        self.att_policy_id = self.contract_id.att_policy_id
        gross_sal = contracts.gross_salary
        basic_sal = contracts.wage
        self.gross_salary = gross_sal
        self.basic_salary = basic_sal
        self.ot_daily_allowance = contracts.ot_daily_allowance

    @api.depends('line_ids.overtime', 'line_ids.diff_time', 'line_ids.late_in', 'line_ids.date','att_policy_id','no_of_total_days')
    def _compute_sheet_total(self):
        """
        Compute Total overtime,late ,absence,diff time and worked hours
        :return:
        """
        for sheet in self:
            # Compute Total Presence
            #presence_lines = sheet.line_ids.filtered(lambda l: l.pl_sign_in > 0 and l.status is False)
            presence_lines = sheet.line_ids.filtered(lambda l: l.status is False)
            sheet.tot_presence = sum([(l.ac_sign_out - l.ac_sign_in) for l in presence_lines])
            sheet.no_presence = len(presence_lines)

            # Compute Total Weekend
            weekend_lines = sheet.line_ids.filtered(lambda l: l.status == 'weekend')
            sheet.no_weekend = len(weekend_lines)

            # Compute Total Public Holiday
            ph_lines = sheet.line_ids.filtered(lambda l: l.status == 'ph')
            sheet.no_ph = len(ph_lines)

            # Compute Total Overtime
            overtime_lines = sheet.line_ids.filtered(lambda l: l.overtime > 0)
            sheet.tot_overtime = sum([l.overtime for l in overtime_lines])
            sheet.no_overtime = len(overtime_lines)
            # Compute Total Late In
            late_lines = sheet.line_ids.filtered(lambda l: l.late_in > 0).mapped('late_in')
            late_lines_abs_in = sheet.line_ids.filtered(lambda l: l.late_in_abs > 0).mapped('late_in')
            late_lines_abs = sheet.line_ids.filtered(lambda l: l.late_in_abs > 0).mapped('late_in_abs')

            no_late = len(late_lines)
            sheet.no_late = no_late
            #sheet.tot_late = sum([l.late_in for l in late_lines])
            sheet.tot_late = sum(late_lines)
            sheet.tot_late_abs = sum(late_lines_abs_in)

            no_late_abs = len(late_lines_abs)
            sheet.no_late_abs = no_late_abs
            #sheet.actual_abs_count_late = sum([l.late_in_abs for l in late_lines_abs])
            sheet.actual_abs_count_late = sum(late_lines_abs)

            try:
                sheet.actual_late_count = (no_late - no_late_abs) / sheet.att_policy_id.salary_ded_count_late
            except:
                sheet.actual_late_count = 0

            # Compute Absence
            absence_lines = sheet.line_ids.filtered(
                lambda l: l.status == "ab")
            sheet.tot_absence = sum([l.diff_time for l in absence_lines])
            sheet.no_absence = len(absence_lines)
            leave_lines = sheet.line_ids.filtered(
                lambda l: l.status == "leave")
            sheet.no_leave = len(leave_lines)

            line_days = len(set(sheet.line_ids.mapped('date')))
            if sheet.att_policy_id.is_att_join_resign:
                no_join_resign_ded_count = sheet.no_of_total_days - line_days
            else:
                no_join_resign_ded_count = 0
                if sheet.initial_employment_date:
                    if sheet.initial_employment_date > sheet.date_from and sheet.initial_employment_date <= sheet.date_to:
                        day_cnt_from = (sheet.initial_employment_date - sheet.date_from).days #join date include
                        no_join_resign_ded_count += day_cnt_from

                if sheet.is_separated and sheet.separation_date:
                    if sheet.separation_date > sheet.date_from and sheet.separation_date <= sheet.date_to:
                        day_cnt_to = (sheet.date_to - sheet.separation_date).days + 1 #separation_date date exclude so 1 plus
                        no_join_resign_ded_count += day_cnt_to

            #--------------------
            if no_join_resign_ded_count > 0:
                sheet.no_join_resign_ded_count = no_join_resign_ded_count
            else:
                sheet.no_join_resign_ded_count = 0

                # lwp_count
            if sheet.employee_id and sheet.date_from and sheet.date_to:
                leave_count_sql = """
                            SELECT
                            COALESCE(SUM(CASE WHEN hlt.type_code = 'CL' THEN leave_count ELSE 0 END), 0) AS cl, 
                            COALESCE(SUM(CASE WHEN hlt.type_code = 'ML' THEN leave_count ELSE 0 END), 0) AS ml, 
                            COALESCE(SUM(CASE WHEN hlt.type_code = 'LWP' THEN leave_count ELSE 0 END), 0) AS lwp, 
                            COALESCE(SUM(CASE WHEN hlt.type_code in ('PL','EL') THEN leave_count ELSE 0 END), 0) AS pl 
                            FROM (
                            SELECT hl.holiday_status_id, COUNT(hld.id) AS leave_count
                            FROM hr_leave hl
                            JOIN hr_leave_details hld ON hld.leave_id = hl.id
                            WHERE hl.state='validate' AND DATE(hld.leave_date) BETWEEN '{0}' AND '{1}' AND hl.employee_id = {2}
                            GROUP BY hl.holiday_status_id
                            ) leave_tbl
                            LEFT JOIN hr_leave_type hlt ON hlt.id = leave_tbl.holiday_status_id
                            """.format(sheet.date_from, sheet.date_to, sheet.employee_id.id)
                self.env.cr.execute(leave_count_sql)
                leave_data = self.env.cr.dictfetchall()

                sheet.no_lwp = leave_data[0]['lwp'] if leave_data else 0
                sheet.no_cl = leave_data[0]['cl'] if leave_data else 0
                sheet.no_ml = leave_data[0]['ml'] if leave_data else 0
                sheet.no_pl = leave_data[0]['pl'] if leave_data else 0
            else:
                sheet.no_lwp = 0
                sheet.no_cl = 0
                sheet.no_ml = 0
                sheet.no_pl = 0

            # compute early-out
            diff_lines = sheet.line_ids.filtered(
                lambda l: l.diff_time > 0 and l.status != "ab")
            sheet.tot_difftime = sum([l.diff_time for l in diff_lines])
            sheet.no_difftime = len(diff_lines)
            try:
                sheet.actual_diff_count = len(diff_lines) / sheet.att_policy_id.salary_ded_count_early_out
            except:
                sheet.actual_diff_count = 0

            try:
                sheet.actual_abs_count = len(absence_lines) / sheet.att_policy_id.salary_ded_count_abs
            except:
                sheet.actual_abs_count = 0

            att_bonus_condition_check = []

            if sheet.contract_id.is_att_bonus_allowed:
                if any([sheet.att_policy_id.is_absent_allowed_att_bonus, sheet.att_policy_id.is_leave_allowed_att_bonus, sheet.att_policy_id.is_late_allowed_att_bonus, sheet.att_policy_id.is_diff_allowed_att_bonus]):
                    if sheet.att_policy_id.is_absent_allowed_att_bonus:
                        att_bonus_condition_check.append(sheet.att_policy_id.absent_count_att_bonus >= sheet.no_absence)
                    if sheet.att_policy_id.is_leave_allowed_att_bonus:
                        att_bonus_condition_check.append(sheet.att_policy_id.leave_count_att_bonus >= sheet.no_leave)
                    if sheet.att_policy_id.is_late_allowed_att_bonus:
                        att_bonus_condition_check.append(sheet.att_policy_id.late_count_att_bonus >= sheet.no_late)
                    if sheet.att_policy_id.is_diff_allowed_att_bonus:
                        att_bonus_condition_check.append(sheet.att_policy_id.diff_count_att_bonus >= sheet.no_difftime)
                else:
                    sheet.no_att_bonus = 0
            else:
                sheet.no_att_bonus = 0

            if all(att_bonus_condition_check) and att_bonus_condition_check != []:
                sheet.no_att_bonus = 1
            else:
                sheet.no_att_bonus = 0


    def _get_float_from_time(self, time):
        str_time = datetime.strftime(time, "%H:%M")
        split_time = [int(n) for n in str_time.split(":")]
        float_time = split_time[0] + split_time[1] / 60.0
        return float_time

    def get_attendance_intervals(self, employee, day_start, day_end, tz):
        """

        :param employee:
        :param day_start:datetime the start of the day in datetime format
        :param day_end: datetime the end of the day in datetime format
        :return:
        """
        res = []

        #day_start_native = day_start.replace(tzinfo=tz).astimezone(pytz.utc).replace(tzinfo=None)
        #day_end_native = day_end.replace(tzinfo=tz).astimezone(pytz.utc).replace(tzinfo=None)
        # attendances = self.env['hr.attendance'].sudo().search(
        #     [('employee_id.id', '=', employee.id),
        #      ('check_in', '>=', day_start_native),
        #      ('check_in', '<=', day_end_native)],
        #     order="check_in")

        attendance_date_from = day_start.date()
        attendance_date_end = day_end.date()
        attendances = self.env['hr.attendance'].sudo().search(
            [('employee_id.id', '=', employee.id),
             ('attendance_date', '>=', attendance_date_from),
             ('attendance_date', '<=', attendance_date_end)],
            limit=1)

        for att in attendances:
            check_in = att.check_in
            check_out = att.check_out
            if not check_out:
                continue
            res.append((check_in, check_out, att.manual_flag, att.manual_reason))
        return res

    def _get_emp_leave_intervals(self, emp, start_datetime=None,
                                 end_datetime=None):
        leaves = []
        leave_obj = self.env['hr.leave']
        leave_ids = leave_obj.search([
            ('employee_id', '=', emp.id),
            ('state', '=', 'validate')])

        for leave in leave_ids:
            date_from = leave.date_from
            if end_datetime and date_from > end_datetime:
                continue
            date_to = leave.date_to
            if start_datetime and date_to < start_datetime:
                continue
            leaves.append((date_from, date_to))
        return leaves

    def get_public_holiday(self, date, emp):
        public_holiday = []
        public_holidays = self.env['hr.public.holiday'].sudo().search(
            [('date_from', '<=', date), ('date_to', '>=', date),
             ('state', '=', 'active')])
        for ph in public_holidays:
            if not ph.emp_ids:
                return public_holidays
            if emp.id in ph.emp_ids.ids:
                public_holiday.append(ph.id)
        return public_holiday


    # get attendance sheet from attendance details
    def get_attendances(self):
        for att_sheet in self:
            att_sheet.line_ids.unlink()
            att_line = self.env["attendance.sheet.line"].sudo()
            from_date = att_sheet.date_from
            to_date = att_sheet.date_to
            emp = att_sheet.employee_id
            tz = pytz.timezone(emp.tz)
            if not tz:
                raise exceptions.Warning(
                    "Please add time zone for employee : %s" % emp.name)
            calendar_id = emp.contract_id.resource_calendar_id
            if not calendar_id:
                raise ValidationError(_(
                    'Please add working hours to the %s `s contract ' % emp.name))
            policy_id = att_sheet.att_policy_id
            if not policy_id:
                raise ValidationError(_(
                    'Please add Attendance Policy to the %s `s contract ' % emp.name))

            att_obj = self.env['employee.attendance.sheet.line'].search(
                [('date', '>=', from_date), ('date', '<=', to_date), ('employee_id', '=', emp.id)], order='date ASC')

            for rec in att_obj:
                if rec.note:
                    note = rec.note
                else:
                    note = rec.manual_reason

                punch_count = rec.punch_count

                if rec.status == 'leave':
                    leave_id_obj = self.env['hr.leave.details'].sudo().search([('employee_id', '=', rec.employee_id.id),
                                                                    ('leave_date', '=', rec.date)], limit=1)
                    note = leave_id_obj.leave_id.holiday_status_id.type_code or leave_id_obj.leave_id.holiday_status_id.name
                vals = {
                    'att_sheet_id': att_sheet.id,
                    'employee_id': rec.employee_id,
                    'date': rec.date,
                    'day': rec.day,
                    'pl_sign_in': rec.pl_sign_in,
                    'pl_sign_out': rec.pl_sign_out,
                    'ac_sign_in': rec.ac_sign_in,
                    'ac_sign_out': rec.ac_sign_out,
                    'work_hours': rec.work_hours,
                    'worked_hours': rec.worked_hours,
                    'act_late_in': rec.act_late_in,
                    'late_in': rec.late_in,
                    'late_in_abs': rec.late_in_abs,
                    'act_overtime':  rec.act_overtime if rec.overtime > 0 and rec.ovt_flag == '1' else 0.00,
                    'overtime':  rec.overtime if rec.overtime > 0 and rec.ovt_flag == '1' else 0.00,
                    'act_diff_time': rec.act_diff_time,
                    'diff_time': rec.diff_time,
                    'status': rec.status,
                    'note': note if rec.overtime > 0 and rec.ovt_flag == '1' else '',
                    'punch_count': punch_count,
                    'resource_calendar_id': rec.resource_calendar_id.id or None
                }
                att_line.create(vals)

            #-----------
            ndays = 0
            if att_sheet.date_to:
                ndays = monthrange(att_sheet.date_to.year, att_sheet.date_to.month)[1]
            att_sheet.no_of_calendar_days = ndays
            #-----------

            no_of_total_days = 0
            if att_sheet.date_from and att_sheet.date_to:
                no_of_total_days = (att_sheet.date_to - att_sheet.date_from).days + 1
                att_sheet.no_of_total_days = no_of_total_days


            if att_sheet.att_policy_id.work_day_without_week_ph or att_sheet.att_policy_id.work_day_without_ph:
                wk_days = 0
                ph_days = 0
                if att_sheet.att_policy_id.work_day_without_week_ph:
                    wk_list = att_sheet.line_ids.filtered(lambda l: l.status == "weekend").mapped('date')
                    wk_days = len(set(wk_list))
                if att_sheet.att_policy_id.work_day_without_ph:
                    ph_list = att_sheet.line_ids.filtered(lambda l: l.status == "ph").mapped('date')
                    ph_days = len(set(ph_list))

                no_of_days = no_of_total_days - (wk_days + ph_days)
            else:
                no_of_days = no_of_total_days

            att_sheet.no_of_days = no_of_days
            try:
                if att_sheet.att_policy_id.is_per_day_salary_from_workday:
                    if att_sheet.att_policy_id.is_per_day_salary_from_basic:
                        att_sheet.per_day_salary = att_sheet.basic_salary / no_of_days
                    else:
                        att_sheet.per_day_salary = att_sheet.gross_salary / no_of_days
                else:
                    if att_sheet.att_policy_id.is_per_day_salary_from_basic:
                        att_sheet.per_day_salary = att_sheet.basic_salary / att_sheet.no_of_calendar_days
                    else:
                        att_sheet.per_day_salary = att_sheet.gross_salary / att_sheet.no_of_calendar_days

            except:
                att_sheet.per_day_salary = 0

            if policy_id.ot_calc_type == 'fixed':
                att_sheet.ot_day_count = emp.contract_id.ot_day_count
                att_sheet.ot_daily_salary = emp.contract_id.ot_daily_salary
            else:
                att_sheet.ot_day_count = att_sheet.no_of_days

                try:
                    if att_sheet.att_policy_id.is_per_day_salary_from_workday:
                        if att_sheet.att_policy_id.is_per_day_salary_from_basic:
                            att_sheet.ot_daily_salary = att_sheet.basic_salary / att_sheet.no_of_days
                        else:
                            if att_sheet.att_policy_id.is_per_day_salary_from_basic:
                                att_sheet.ot_daily_salary = att_sheet.basic_salary / att_sheet.no_of_days
                            else:
                                att_sheet.ot_daily_salary = att_sheet.gross_salary / att_sheet.no_of_days
                    else:
                        att_sheet.ot_daily_salary = att_sheet.gross_salary / att_sheet.no_of_calendar_days
                except:
                    att_sheet.ot_daily_salary = 0

            # ndays=0
            # if self.date_to:
            #     ndays = monthrange(self.date_to.year, self.date_to.month)[1]
            # self.no_of_calendar_days = ndays

            # if self.date_from and self.date_to:
            #     self.no_of_total_days = (self.date_to-self.date_from).days + 1

            extra_allowance = self.env['employee.attendance.sheet.line'].sudo().search(
                [('date', '>=', from_date), ('date', '<=', to_date), ('employee_id', '=', emp.id),('ovt_flag', '=', '3')])
            att_sheet.no_extra_allowance = (len(extra_allowance))

    def action_payslip(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.payslip_id.id,
            'views': [(False, 'form')],
        }

    def action_create_payslip(self):
        payslip_obj = self.env['hr.payslip']
        for sheet in self:
            if sheet.payslip_id:
                raise ValidationError(_('Payslip Has Been Created Before for %s') % sheet.employee_id.name)

            contract_obj = sheet.employee_id.contract_id or None
            if not contract_obj:
                raise ValidationError(_('Required Contract for %s') % sheet.employee_id.name)
            else:
                pass

            if not contract_obj.struct_id:
                raise ValidationError(_('Required Salary Structure in contract for %s') % sheet.employee_id.name)
            else:
                sal_struct_id = contract_obj.struct_id.id

            disbursement_type = contract_obj.disbursement_type or None
            s_bank_name = contract_obj.s_bank_name or None
            s_bank_account_no = contract_obj.s_bank_account_no or None

            new_payslip = payslip_obj.new({
                'employee_id': sheet.employee_id.id,
                'date_from': sheet.date_from,
                'date_to': sheet.date_to,
                'contract_id': sheet.employee_id.contract_id.id,
                'struct_id': sal_struct_id,
                'disbursement_type': disbursement_type,
                's_bank_name': s_bank_name,
                's_bank_account_no': s_bank_account_no
            })
            new_payslip._onchange_employee()
            payslip_dict = new_payslip._convert_to_write({
                name: new_payslip[name] for name in new_payslip._cache})
            payslip_id = payslip_obj.create(payslip_dict)
            worked_day_lines = self._get_workday_lines()
            payslip_id.worked_days_line_ids = [(0, 0, x) for x in
                                               worked_day_lines]

            payslip_id.compute_sheet()
            sheet.payslip_id = payslip_id

    def _get_workday_lines(self):
        self.ensure_one()
        contract = self.contract_id
        work_entry_obj = self.env['hr.work.entry.type']
        work_entry_types = self.contract_id.struct_id.unpaid_work_entry_type_ids if self.contract_id.struct_id else self.contract_id.structure_type_id.default_struct_id.unpaid_work_entry_type_ids
        if not work_entry_types:
            raise ValidationError(_(
                "Please Add Unpaid Work Entry To %s Salary Structure" % self.contract_id.name))

        work_entry_type = work_entry_types[0]

        daily_alw_work_entry = work_entry_obj.search([('code', '=', 'ATTSHDLA')])
        overtime_alw_work_entry = work_entry_obj.search([('code', '=', 'ATTSHOTA')])
        overtime_work_entry = work_entry_obj.search([('code', '=', 'ATTSHOT')])
        att_bonus_work_entry = work_entry_obj.search([('code', '=', 'ATTSHBONUS')])
        latein_work_entry = work_entry_obj.search([('code', '=', 'ATTSHLI')])
        absence_work_entry = work_entry_obj.search([('code', '=', 'ATTSHAB')])
        late_absence_work_entry = work_entry_obj.search([('code', '=', 'ATTSHABLI')])
        difftime_work_entry = work_entry_obj.search([('code', '=', 'ATTSHDT')])
        lwp_work_entry = work_entry_obj.search([('code', '=', 'ATTSHLWP')])
        tiff_work_entry = work_entry_obj.search([('code', '=', 'ATTSHTIFFIN')])
        ml_work_entry = work_entry_obj.search([('code', '=', 'ATTSHML')])
        extra_alw_work_entry = work_entry_obj.search([('code', '=', 'ATTSHEA')])
        jrd_work_entry = work_entry_obj.search([('code', '=', 'ATTSJRD')])

        if not daily_alw_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Daily Allowance With Code ATTSHDLA'))
        if not overtime_alw_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Overtime Allowance With Code ATTSHOTA'))
        if not overtime_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Overtime With Code ATTSHOT'))
        if not att_bonus_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Bonus With Code ATTSHBONUS'))
        if not latein_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Late In With Code ATTSHLI'))
        if not absence_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Absence With Code ATTSHAB'))
        if not late_absence_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Late Absence With Code ATTSHABLI'))
        if not difftime_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Diff Time With Code ATTSHDT'))
        if not lwp_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For LWP Leave With Code ATTSHLWP'))
        if not tiff_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Tiffin Allowance With Code ATTSHTIFFIN'))
        if not ml_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Medical leave Deduction With Code ATTSHML'))
        if not extra_alw_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Extra Allowance With Code ATTSHEA'))
        if not jrd_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Join/Resign With Code ATTSJRD'))

        daily_allowance = [{
            'name': "Daily Allowance",
            'code': 'ATTSHDLA',
            'work_entry_type_id': daily_alw_work_entry[0].id,
            'sequence': 27,
            'number_of_days': self.no_presence,
            'amount': self.contract_id.daily_allowance * self.no_presence
        }]

        ot_allowances = [{
            'name': "Overtime Allowance",
            'code': 'ATTSHOTA',
            'work_entry_type_id': overtime_alw_work_entry[0].id,
            'sequence': 25,
            'number_of_days': self.no_overtime,
            'number_of_hours': self.tot_overtime,
            'amount': self.ot_daily_allowance * self.no_overtime
        }]
        if contract.ot_type == 'daily':
            overtime_amt = self.ot_daily_salary * self.no_overtime
        else:
            ot_mint = ((timedelta(hours=math.modf(self.tot_overtime)[0]) + timedelta(seconds=30)).seconds // 60) % 60
            overtime_amt = (contract.ot_hourly_rate * int(self.tot_overtime)) + (
                        contract.ot_hourly_rate * (ot_mint / 60))
        att_bonus = [{
            'name': "Attendance Bonus",
            'code': 'ATTBONUS',
            'work_entry_type_id': att_bonus_work_entry[0].id,
            'sequence': 25,
            'number_of_days': self.no_att_bonus,
            'number_of_hours': self.tot_presence,
            'amount': contract.att_bonus_rate * self.no_att_bonus
        }]
        overtime = [{
            'name': "Overtime",
            'code': 'ATTSHOT',
            'work_entry_type_id': overtime_work_entry[0].id,
            'sequence': 30,
            'number_of_days': self.no_overtime,
            'number_of_hours': self.tot_overtime,
            'amount': overtime_amt
        }]
        absence = [{
            'name': "Absence",
            'code': 'ATTSHAB',
            'work_entry_type_id': absence_work_entry[0].id,
            'sequence': 35,
            'number_of_days': self.no_absence,
            'number_of_hours': self.tot_absence,
            'amount': self.per_day_salary * self.no_absence
        }]
        late_absence = [{
            'name': "Late Absence",
            'code': 'ATTSHABLI',
            'work_entry_type_id': late_absence_work_entry[0].id,
            'sequence': 51,
            'number_of_days': self.actual_abs_count_late,
            'number_of_hours': self.tot_late_abs,
            'amount': self.per_day_salary * self.actual_abs_count_late
        }]
        join_resign_ded = [{
            'name': "Join/Resign Deduction",
            'code': 'ATTSJRD',
            'work_entry_type_id': jrd_work_entry[0].id,
            'sequence': 36,
            'number_of_days': self.no_join_resign_ded_count,
            'amount': self.per_day_salary * self.no_join_resign_ded_count
        }]

        leave_lwp = [{
            'name': "LWP",
            'code': 'ATTSHLWP',
            'work_entry_type_id': lwp_work_entry[0].id,
            'sequence': 37,
            'number_of_days': self.no_lwp,
            'amount': self.per_day_salary * self.no_lwp
        }]
        late = [{
            'name': "Late In",
            'code': 'ATTSHLI',
            'work_entry_type_id': latein_work_entry[0].id,
            'sequence': 40,
            'number_of_days': self.actual_late_count,
            'number_of_hours': self.tot_late,
            'amount': self.per_day_salary * self.actual_late_count
        }]
        difftime = [{
            'name': "Difference time",
            'code': 'ATTSHDT',
            'work_entry_type_id': difftime_work_entry[0].id,
            'sequence': 45,
            'number_of_days': self.actual_diff_count,
            'number_of_hours': self.tot_difftime,
            'amount': self.per_day_salary * self.actual_diff_count
        }]
        if self.no_of_calendar_days > 0:
            extra_alw = [{
                'name': "Extra Allowance",
                'code': 'ATTSHEA',
                'work_entry_type_id': extra_alw_work_entry[0].id,
                'sequence': 46,
                'number_of_days': self.no_extra_allowance,
                'amount': self.no_extra_allowance * (self.gross_salary/self.no_of_calendar_days)
            }]
            ml_deduction = [{
                'name': "Medical Leave Deduction",
                'code': 'ATTSHML',
                'work_entry_type_id': ml_work_entry[0].id,
                'sequence': 50,
                'number_of_days': self.no_ml,
                'amount': (self.basic_salary/self.no_of_calendar_days) * self.no_ml #(self.no_ml/2)
            }]
        else:
            raise UserError(_('Required No. of Calendar Days!'))

        per_day_tiffin=0
        if self.contract_id.is_tiffin_alw_allowed:
            if self.contract_id.tiffin_alw_type=="0":
                per_day_tiffin = self.contract_id.tiffin_allowance
            elif self.contract_id.tiffin_alw_type=="1":
                try:
                    per_day_tiffin = round(self.contract_id.tiffin_allowance/self.no_of_days, 2)
                except:
                    per_day_tiffin = 0

        is_tiffin_allowed_absent=self.att_policy_id.is_tiffin_allowed_absent
        is_tiffin_allowed_leave=self.att_policy_id.is_tiffin_allowed_leave
        tiffin_days = self.no_of_days - (self.no_join_resign_ded_count+self.no_absence+self.no_leave)
        if is_tiffin_allowed_absent==True:
            tiffin_days = tiffin_days+self.no_absence
        if is_tiffin_allowed_leave==True:
            tiffin_days = tiffin_days+self.no_leave

        tiffin_amount = round(per_day_tiffin * tiffin_days,0)

        tiffin_day = self.no_presence
        tiffin = [{
            'name': "Tiffin Allowance",
            'code': 'ATTSHTIFFIN',
            'work_entry_type_id': tiff_work_entry[0].id,
            'sequence': 46,
            'number_of_days': tiffin_day,
            'number_of_hours': self.tot_presence,
            'amount': tiffin_amount
        }]
        worked_days_lines = att_bonus + daily_allowance + ot_allowances + overtime + extra_alw + late + absence + late_absence + join_resign_ded + difftime + leave_lwp + tiffin + ml_deduction
        return worked_days_lines



class AttendanceSheetLine(models.Model):
    _name = 'attendance.sheet.line'
    _description = 'Attendance Sheet Line'


    state = fields.Selection(related='att_sheet_id.state', store=True)

    date = fields.Date("Date")
    day = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], 'Day of Week', required=True, index=True)
    att_sheet_id = fields.Many2one(comodel_name='attendance.sheet',
                                   ondelete="cascade",
                                   string='Attendance Sheet', readonly=True)
    employee_id = fields.Many2one(related='att_sheet_id.employee_id',
                                  string='Employee')
    pl_sign_in = fields.Float("Planned sign in", readonly=True)
    pl_sign_out = fields.Float("Planned sign out", readonly=True)
    work_hours = fields.Float("Work Hours", readonly=True)
    worked_hours = fields.Float("Worked Hours for OT", readonly=True)
    ac_sign_in = fields.Float("Actual sign in", readonly=True)
    ac_sign_out = fields.Float("Actual sign out", readonly=True)
    overtime = fields.Float("Overtime", readonly=True)
    act_overtime = fields.Float("Actual Overtime", readonly=True)
    late_in = fields.Float("Late In", readonly=True)
    late_in_abs = fields.Float("Late In Abs", default=0, readonly=True)
    diff_time = fields.Float("Diff Time",
                             help="Diffrence between the working time and attendance time(s) ",
                             readonly=True)
    act_late_in = fields.Float("Actual Late In", readonly=True)
    act_diff_time = fields.Float("Actual Diff Time",
                                 help="Diffrence between the working time and attendance time(s) ",
                                 readonly=True)
    status = fields.Selection(string="Status",
                              selection=[('ab', 'Absence'),
                                         ('weekend', 'Week End'),
                                         ('ph', 'Public Holiday'),
                                         ('leave', 'Leave'), ],
                              required=False, readonly=True)
    note = fields.Text("Note", readonly=True)
    punch_count = fields.Integer(string='Punch Count', default=1)

    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Shift',
                                           help="Employee's working schedule.")
    is_over_ride_day = fields.Boolean(string="Over-Ride Shift", related='resource_calendar_id.is_over_ride_day')

