from odoo import models, fields, tools, api, exceptions, _

import pytz
from datetime import datetime, date, timedelta, time
from odoo.exceptions import UserError, ValidationError


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    _description = 'Inherited HR Attendance'

    checkin_device_id = fields.Many2one('attendance.device', string='Checkin Device', readonly=True, index=True,
                                        help='The device with which user took check in action')
    checkout_device_id = fields.Many2one('attendance.device', string='Checkout Device', readonly=True, index=True,
                                         help='The device with which user took check out action')
    activity_id = fields.Many2one('attendance.activity', string='Attendance Activity',
                                  help='This field is to group attendance into multiple Activity (e.g. Overtime, Normal Working, etc)')

    job_id = fields.Many2one('hr.job', string="Designation", related="employee_id.job_id", readonly=True)
    emp_card_no = fields.Char(string="Employee ID", related='employee_id.id_card_no')

    id_card_no = fields.Char(string="Employee ID", groups="hr.group_hr_user",
                             related='employee_id.id_card_no')
    device_user_id = fields.Char(string='Biometric Device ID',
                                 related='employee_id.device_user_id')
    check_in_location = fields.Char(string="Check In Location")
    check_out_location = fields.Char(string="Check Out Location")
    # -----------
    attendance_date = fields.Date(string='Date', index=True)
    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], 'Day of Week', compute='_compute_dayofweek', store=True)

    user_work_location_id = fields.Many2one('stock.location', string="Work/Job Location", ondelete='restrict')

    manual_flag = fields.Integer(string='Manual?', default=0, help="Manual Attendance?")
    active = fields.Boolean(string='Active', default=True)
    manual_reason = fields.Text(string='Manual Reason', default='')

    # ------------
    pl_sign_in = fields.Float("Planned sign in", default=0, readonly=True)
    pl_sign_out = fields.Float("Planned sign out", default=0, readonly=True)
    pl_sign_in_time = fields.Datetime(string='Planned IN', default=0, required=False)
    pl_sign_out_time = fields.Datetime(string='Planned OUT', default=0, required=False)

    late_in = fields.Float(string='Late In', default=0, readonly=True)
    late_in_abs = fields.Float(string='Late In Abs', default=0, readonly=True)
    diff_time = fields.Float(string='Early Out', default=0, readonly=True)
    act_late_in = fields.Float("Actual Late In", default=0, readonly=True)
    act_diff_time = fields.Float("Actual Early Out", help="Difference between the working time and attendance time(s) ",
                                 default=0, readonly=True)
    overtime = fields.Float("Overtime", default=0, readonly=True)
    act_overtime = fields.Float("Actual Overtime", default=0, readonly=True)
    #----------------
    
    note = fields.Text("Note", readonly=True)
    status = fields.Selection(string="Status",
                              selection=[('ab', 'Absence'),
                                         ('weekend', 'Week End'),
                                         ('ph', 'Public Holiday'),
                                         ('leave', 'Leave'), ],
                              required=False, readonly=True)

    # policy_process = fields.Integer(string='Policy Apply?', default = 0)
    policy_process = fields.Selection([
        ('0', 'Pending'),
        ('1', 'Done'),
        ('2', 'Error-TZ'),
        ('3', 'Error-Work Schedule'),
        ('4', 'Error-Policy'),
        ('5', 'Error-Emp.Not Running'),
        ('6', 'Error-Invaid Date')
    ], string='Policy Apply?', default='0', index=True)

    punch_count = fields.Integer(string='Punch Count', default=1)

    manual_absent = fields.Boolean(string='Absent?', default=False, help="Manual Absent?")
    manual_weekend = fields.Boolean('Weekend Alter?', default=False, help="Manual Weekend Alter?")

    manual_uid = fields.Many2one('res.users', string='Last Manual Edited By')
    manual_time = fields.Datetime(string='Last Manual Time')

    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Shift (Today)',
                                           help="Employee's working schedule.")
    is_over_ride_day = fields.Boolean(default=False, string="Over-Ride Shift (Today)")

    resource_calendar_id_prev = fields.Many2one('resource.calendar', string='Working Shift (Previous Day)',
                                           help="Employee's working schedule.")
    is_over_ride_day_prev = fields.Boolean(default=False, string="Over-Ride Shift (Previous Day)")



    @api.depends('attendance_date')
    def _compute_dayofweek(self):
        for attendance in self:
            if attendance.attendance_date:
                # getting attendance date
                attendance_date = attendance.attendance_date

                attendance_day = datetime.strptime(str(attendance_date), '%Y-%m-%d').strftime('%a').upper()
                # employee_id = attendance.employee_id
                # ---------- for dynamic hour
                day_no = ''
                if attendance_day == 'SAT':
                    day_no = '5'
                elif attendance_day == 'SUN':
                    day_no = '6'
                elif attendance_day == 'MON':
                    day_no = '0'
                elif attendance_day == 'TUE':
                    day_no = '1'
                elif attendance_day == 'WED':
                    day_no = '2'
                elif attendance_day == 'THU':
                    day_no = '3'
                elif attendance_day == 'FRI':
                    day_no = '4'

                attendance.dayofweek = day_no

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        if not self.env.context.get('synch_ignore_constraints', False):
            super(HrAttendance, self)._check_validity()

    #transfer func to att sheet
    # def set_attendance_policy_data(self):
    #     att_obj = self.env["hr.attendance"].sudo()
    #
    #     for hr_att in self:
    #         # hr_att.line_ids.unlink()
    #         # att_line = self.env["attendance.sheet.line"]
    #         from_date = hr_att.attendance_date
    #         to_date = hr_att.attendance_date
    #         emp = hr_att.employee_id
    #
    #         is_running_emp = True
    #         initial_employment_date = emp.initial_employment_date
    #         if not hr_att.attendance_date:
    #             hr_att.policy_process = '6'
    #             continue
    #
    #         if not initial_employment_date or initial_employment_date > hr_att.attendance_date:
    #             is_running_emp = False
    #         else:
    #             is_separated = emp.is_separated
    #             if is_separated:
    #                 separation_date = emp.separation_date
    #                 if separation_date and separation_date < hr_att.attendance_date:
    #                     is_running_emp = False
    #
    #         if emp.active == False or is_running_emp == False:
    #             hr_att.policy_process = '5'
    #             hr_att.pl_sign_in = 0
    #             hr_att.pl_sign_out = 0
    #             hr_att.late_in = 0
    #             hr_att.diff_time = 0
    #             hr_att.act_late_in = 0
    #             hr_att.act_diff_time = 0
    #             hr_att.overtime = 0
    #             hr_att.act_overtime = 0
    #             continue
    #
    #         tz = pytz.timezone(emp.tz)
    #         if not tz:
    #             hr_att.policy_process = '2'
    #             hr_att.pl_sign_in = 0
    #             hr_att.pl_sign_out = 0
    #             hr_att.late_in = 0
    #             hr_att.diff_time = 0
    #             hr_att.act_late_in = 0
    #             hr_att.act_diff_time = 0
    #             hr_att.overtime = 0
    #             hr_att.act_overtime = 0
    #             continue
    #             # raise exceptions.Warning(
    #             #     "Please add time zone for employee : %s" % emp.name)
    #         calendar_id = emp.contract_id.resource_calendar_id
    #         if not calendar_id:
    #             hr_att.policy_process = '3'
    #             hr_att.pl_sign_in = 0
    #             hr_att.pl_sign_out = 0
    #             hr_att.late_in = 0
    #             hr_att.diff_time = 0
    #             hr_att.act_late_in = 0
    #             hr_att.act_diff_time = 0
    #             hr_att.overtime = 0
    #             hr_att.act_overtime = 0
    #             continue
    #             # raise ValidationError(_(
    #             #     'Please add working hours to the %s `s contract ' % emp.name))
    #
    #         policy_id = hr_att.employee_id.contract_id.att_policy_id
    #         if not policy_id:
    #             hr_att.policy_process = '4'
    #             hr_att.pl_sign_in = 0
    #             hr_att.pl_sign_out = 0
    #             hr_att.late_in = 0
    #             hr_att.diff_time = 0
    #             hr_att.act_late_in = 0
    #             hr_att.act_diff_time = 0
    #             hr_att.overtime = 0
    #             hr_att.act_overtime = 0
    #             continue
    #             # raise ValidationError(_(
    #             #     'Please add Attendance Policy to the %s `s contract ' % emp.name))
    #
    #         att_obj.employee_attendance_data_process(emp, from_date, to_date, hr_att)
    #
    #         continue
    #
    #         # unused below code for processing all data in a functin employee_attendance_data_process
    #
    #         # ====================
    #         # UNUSED CODE below
    #
    #     return True

    def update_manual_reason_note(self):
        att_obj = self.env["hr.attendance"].sudo()
        action_vals = {
            'name': _('Update Manual Reason/Note'),
            # 'domain': [('id', 'in', account_move_obj.ids)],
            'res_model': 'update.manual.reason.note.wizard',
            'view_mode': 'form',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {'active_id': self.id},
            'target': 'new',
        }
        return action_vals

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
        #base
        # day_start_native = day_start.replace(tzinfo=tz).astimezone(
        #     pytz.utc).replace(tzinfo=None)
        # day_end_native = day_end.replace(tzinfo=tz).astimezone(
        #     pytz.utc).replace(tzinfo=None)
        res = []
        # attendances = self.env['hr.attendance'].sudo().search(
        #     [('employee_id.id', '=', employee.id),
        #      ('check_in', '>=', day_start_native),
        #      ('check_in', '<=', day_end_native)],
        #     order="check_in")

        #custom
        attendance_date = day_start.date()
        attendances = self.env['hr.attendance'].sudo().search(
            [('employee_id.id', '=', employee.id),
             ('attendance_date', '=', attendance_date)],
            limit=1)

        for att in attendances:
            check_in = att.check_in
            check_out = att.check_out
            if not check_out:
                continue
            res.append((check_in, check_out))
        return res

    def _get_emp_leave_intervals(self, emp, start_datetime=None,
                                 end_datetime=None):
        leaves = []
        leaves_note = []
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
            leaves_note.append(leave.name)
        return (leaves, leaves_note)

    def get_public_holiday(self, date, emp):
        public_holiday = []
        public_holidays = self.env['hr.public.holiday'].sudo().search([('date_from', '<=', date), ('date_to', '>=', date),
             ('state', '=', 'active')])
        for ph in public_holidays:
            if not ph.emp_ids:
                return public_holidays
            if emp.id in ph.emp_ids.ids:
                public_holiday.append(ph)
        return public_holiday

    # def employee_attendance_data_process(self, employee, from_dt, to_dt, hr_att=None):
    #     from_date = from_dt
    #     to_date = to_dt
    #     emp = employee
    #     # -----------
    #     # employee time zone
    #     tz = pytz.timezone(emp.tz)
    #     if not tz:
    #         return True
    #
    #     # employee work schedule
    #     calendar_id = emp.contract_id.resource_calendar_id
    #     if not calendar_id:
    #         return True
    #     is_rostering_employee = emp.is_rostering_employee or False
    #
    #     # employee attendance policy
    #     policy_id = emp.contract_id.att_policy_id
    #     if not policy_id:
    #         return True
    #
    #     # manual_flag = False
    #     # manual_reason = ''
    #     # if hr_att:
    #     #     manual_flag = hr_att.manual_flag
    #     #     manual_reason = hr_att.manual_reason
    #
    #     all_dates = [(from_date + timedelta(days=x)) for x in range((to_date - from_date).days + 1)]
    #     abs_cnt = 0
    #
    #     # CHECK-IN valid time period from attendance policy otherwise absent
    #     check_in_start = timedelta(hours=int(policy_id.check_in_start), minutes=(policy_id.check_in_start * 60) % 60,
    #                                seconds=0)
    #     check_in_end = timedelta(hours=int(policy_id.check_in_end), minutes=(policy_id.check_in_end * 60) % 60,
    #                              seconds=0)
    #
    #     att_line = self.env["employee.attendance.sheet.line"].sudo()
    #
    #     status = ''
    #     for day in all_dates:
    #         #----------- befoe joining date and after separation date
    #         # if not emp.initial_employment_date or emp.initial_employment_date > day:
    #         #     continue
    #         # else:
    #         #     if emp.is_separated:
    #         #         separation_date = emp.separation_date
    #         #         if separation_date and separation_date < day:
    #         #             continue
    #
    #         #---------------
    #         day_start = datetime(day.year, day.month, day.day)
    #         day_end = day_start.replace(hour=23, minute=59,
    #                                     second=59)
    #         day_str = str(day.weekday())
    #         date = day.strftime('%Y-%m-%d')
    #         # print('date========',date)
    #         #---------------
    #         if is_rostering_employee:
    #             calendar_id = self.get_emp_shifting_schedule(date, emp)
    #
    #         #----------------
    #         work_intervals = calendar_id.att_get_work_intervals(day_start,
    #                                                             day_end, tz)
    #         attendance_intervals = self.get_attendance_intervals(emp,
    #                                                              day_start,
    #                                                              day_end,
    #                                                              tz)
    #         leaves = []
    #         leaves_note = ''
    #         public_holiday = self.get_public_holiday(date, emp)
    #         if not public_holiday:
    #             leaves_list = self._get_emp_leave_intervals(emp, day_start, day_end)
    #             leaves = leaves_list[0]
    #             leaves_note = leaves_list[1][0] if leaves_list[1] else ''
    #
    #         reserved_intervals = []
    #         overtime_policy = policy_id.get_overtime()
    #         abs_flag = False
    #         # -----------
    #         att_line_obj = att_line.search([('employee_id.id', '=', emp.id), ('date', '=', date)], limit=1)
    #         hr_att1 = None
    #
    #         manual_flag = False
    #         manual_reason = ''
    #         punch_count = 0
    #         if hr_att:
    #             manual_flag = hr_att.manual_flag
    #             manual_reason = hr_att.manual_reason
    #             punch_count = hr_att.punch_count
    #             manual_absent = hr_att.manual_absent
    #             if manual_absent:
    #                 hr_att.status = 'ab'
    #                 hr_att.policy_process = '1'
    #                 continue
    #         else:
    #             hr_att1 = self.env['hr.attendance'].sudo().search(
    #                 [('employee_id.id', '=', emp.id), ('attendance_date', '=', date)],
    #                 limit=1)  # ('policy_process', '=', '0')
    #             if hr_att1:
    #                 manual_flag = hr_att1.manual_flag
    #                 manual_reason = hr_att1.manual_reason
    #                 punch_count = hr_att1.punch_count
    #                 manual_absent = hr_att1.manual_absent
    #                 if manual_absent:
    #                     hr_att1.status = 'ab'
    #                     hr_att1.policy_process = '1'
    #                     continue
    #
    #         # --------
    #         if work_intervals:
    #             # public holiday process
    #             if public_holiday:
    #                 # working in public holiday
    #                 if attendance_intervals:
    #                     for attendance_interval in attendance_intervals:
    #                         overtime = attendance_interval[1] - \
    #                                    attendance_interval[0]
    #                         float_overtime = overtime.total_seconds() / 3600
    #                         if float_overtime <= overtime_policy[
    #                             'ph_after']:
    #                             act_float_overtime = float_overtime = 0
    #                         else:
    #                             act_float_overtime = (float_overtime -
    #                                                   overtime_policy[
    #                                                       'ph_after'])
    #                             float_overtime = (float_overtime -
    #                                               overtime_policy[
    #                                                   'ph_after']) * \
    #                                              overtime_policy['ph_rate']
    #                         ac_sign_in = pytz.utc.localize(
    #                             attendance_interval[0]).astimezone(tz)
    #                         float_ac_sign_in = self._get_float_from_time(
    #                             ac_sign_in)
    #                         ac_sign_out = pytz.utc.localize(
    #                             attendance_interval[1]).astimezone(tz)
    #                         worked_hours = attendance_interval[1] - \
    #                                        attendance_interval[0]
    #                         float_worked_hours = worked_hours.total_seconds() / 3600
    #                         # float_ac_sign_out = float_ac_sign_in + float_worked_hours
    #                         float_ac_sign_out = self._get_float_from_time(
    #                             ac_sign_out)
    #
    #                         values = {
    #                             'employee_id': emp.id,
    #                             'date': date,
    #                             'day': day_str,
    #                             'ac_sign_in': float_ac_sign_in,
    #                             'ac_sign_out': float_ac_sign_out,
    #                             'worked_hours': float_worked_hours,
    #                             'overtime': float_overtime,
    #                             'act_overtime': act_float_overtime,
    #                             'status': 'ph',
    #                             'note': "working on Public Holiday (%s)" %(public_holiday[0].name),
    #                             'manual_flag': manual_flag,
    #                             'manual_reason': manual_reason,
    #                             'punch_count': punch_count
    #                         }
    #                         if att_line_obj:
    #                             if att_line_obj.ovt_flag=='1' and float_overtime==0:
    #                                 float_overtime = float_worked_hours
    #                                 act_float_overtime = float_worked_hours
    #
    #                             write_vals = {
    #                                 'pl_sign_in': 0,
    #                                 'pl_sign_out': 0,
    #                                 'late_in': 0,
    #                                 'act_late_in': 0,
    #                                 'diff_time': 0,
    #                                 'act_diff_time': 0,
    #                                 'ac_sign_in': float_ac_sign_in,
    #                                 'ac_sign_out': float_ac_sign_out,
    #                                 'worked_hours': float_worked_hours,
    #                                 'overtime': float_overtime,
    #                                 'act_overtime': act_float_overtime,
    #                                 'status': 'ph',
    #                                 'note': "working on Public Holiday (%s)" %(public_holiday[0].name),
    #                                 'manual_flag': manual_flag,
    #                                 'manual_reason': manual_reason,
    #                                 'punch_count': punch_count
    #                             }
    #                             att_line_obj.write(write_vals)
    #                         else:
    #                             att_line.create(values)
    #
    #                         status = 'ph'
    #                         if hr_att:
    #                             hr_att.overtime = float_overtime
    #                             hr_att.act_overtime = act_float_overtime
    #                         if hr_att1:
    #                             hr_att1.overtime = float_overtime
    #                             hr_att1.act_overtime = act_float_overtime
    #
    #                 # public holiday
    #                 else:
    #                     tmp_status = 'ph'
    #                     tmp_note = ''
    #                     check_leave = self._check_hr_leave(emp.id, date)
    #                     if check_leave[0]:
    #                         tmp_status = 'leave'
    #                         tmp_note = check_leave[1]
    #                     else:
    #                         tmp_note = public_holiday[0].name
    #
    #                     values = {
    #                         'employee_id': emp.id,
    #                         'date': date,
    #                         'day': day_str,
    #                         'status': tmp_status,
    #                         'note': tmp_note,
    #                     }
    #                     if att_line_obj:
    #                         write_vals = {
    #                             'pl_sign_in': 0,
    #                             'pl_sign_out': 0,
    #                             'worked_hours': 0,
    #                             'ac_sign_in': 0,
    #                             'ac_sign_out': 0,
    #                             'late_in': 0,
    #                             'act_late_in': 0,
    #                             'overtime': 0,
    #                             'act_overtime': 0,
    #                             'diff_time': 0,
    #                             'act_diff_time': 0,
    #                             'note': tmp_note,
    #                             'status': tmp_status,
    #                             'manual_flag': manual_flag,
    #                             'manual_reason': manual_reason,
    #                             'punch_count': punch_count
    #                         }
    #                         att_line_obj.write(write_vals)
    #                     else:
    #                         att_line.create(values)
    #                     status = 'ph'
    #
    #             # working day process
    #             else:
    #                 for i, work_interval in enumerate(work_intervals):
    #                     float_worked_hours = 0
    #                     att_work_intervals = []
    #                     diff_intervals = []
    #                     late_in_interval = []
    #                     diff_time = timedelta(hours=0, minutes=0, seconds=0)
    #                     late_in = timedelta(hours=0, minutes=0, seconds=0)
    #                     overtime = timedelta(hours=0, minutes=0, seconds=0)
    #                     for j, att_interval in enumerate(attendance_intervals):
    #                         # check in time
    #                         check_in_time = att_interval[0]
    #                         # work interval including check in start time from attendance policy
    #                         work_in_with_check_in_start = (work_interval[0] - check_in_start)
    #                         # work interval including check in end time from attendance policy
    #                         work_in_with_check_in_end = (work_interval[0] + check_in_end)
    #
    #                         if work_in_with_check_in_start < check_in_time < work_in_with_check_in_end:
    #                             #print('work_in_with_check_in_start------',work_in_with_check_in_start)
    #                             #print('check_in_time------',check_in_time)
    #                             #print('work_in_with_check_in_end------',work_in_with_check_in_end)
    #
    #                             current_att_interval = att_interval
    #                             if i + 1 < len(work_intervals):
    #                                 next_work_interval = work_intervals[i + 1]
    #                                 if max(next_work_interval[0], current_att_interval[0]) < min(next_work_interval[1],
    #                                                                                              current_att_interval[
    #                                                                                                  1]):
    #                                     split_att_interval = (next_work_interval[0], current_att_interval[1])
    #                                     current_att_interval = (current_att_interval[0], next_work_interval[0])
    #                                     attendance_intervals[j] = current_att_interval
    #                                     attendance_intervals.insert(j + 1, split_att_interval)
    #                             att_work_intervals.append(current_att_interval)
    #
    #                     reserved_intervals += att_work_intervals
    #                     pl_sign_in = self._get_float_from_time(pytz.utc.localize(work_interval[0]).astimezone(tz))
    #                     pl_sign_out = self._get_float_from_time(pytz.utc.localize(work_interval[1]).astimezone(tz))
    #                     pl_sign_in_time = pytz.utc.localize(work_interval[0]).astimezone(tz)
    #                     pl_sign_out_time = pytz.utc.localize(work_interval[1]).astimezone(tz)
    #                     # pl_sign_in2 = timedelta(hours=int(pl_sign_in), minutes=(pl_sign_in*60) % 60, seconds=00)
    #                     # pl_sign_out2 = timedelta(hours=int(pl_sign_out), minutes=(pl_sign_out*60) % 60, seconds=00)
    #                     # pl_sign_in_time2 = day_start + pl_sign_in2 - timedelta(hours=6)
    #                     # pl_sign_out_time2 = day_start + pl_sign_out2 - timedelta(hours=6)
    #
    #                     pl_sign_in_time2 = pl_sign_in_time.replace(tzinfo=tz).astimezone(pytz.utc).replace(
    #                         tzinfo=None) + timedelta(minutes=2)
    #                     pl_sign_out_time2 = pl_sign_out_time.replace(tzinfo=tz).astimezone(pytz.utc).replace(
    #                         tzinfo=None) + timedelta(minutes=2)
    #
    #                     ac_sign_in = 0
    #                     ac_sign_out = 0
    #                     status = ""
    #                     note = ""
    #                     if att_work_intervals:
    #                         if len(att_work_intervals) > 1:
    #                             # print("there is more than one interval for that work interval")
    #                             late_in_interval = (work_interval[0], att_work_intervals[0][0])
    #                             overtime_interval = (work_interval[1], att_work_intervals[-1][1])
    #                             if overtime_interval[1] < overtime_interval[0]:
    #                                 overtime = timedelta(hours=0, minutes=0, seconds=0)
    #                             else:
    #                                 overtime = overtime_interval[1] - overtime_interval[0]
    #                             remain_interval = (att_work_intervals[0][1], work_interval[1])
    #                             # print'first remain intervals is',remain_interval
    #                             for att_work_interval in att_work_intervals:
    #                                 float_worked_hours += (att_work_interval[1] - att_work_interval[
    #                                     0]).total_seconds() / 3600
    #                                 # print'float worked hors is', float_worked_hours
    #                                 if att_work_interval[1] <= remain_interval[0]:
    #                                     continue
    #                                 if att_work_interval[0] >= remain_interval[1]:
    #                                     break
    #                                 if remain_interval[0] < att_work_interval[0] < remain_interval[1]:
    #                                     diff_intervals.append((remain_interval[0], att_work_interval[0]))
    #                                     remain_interval = (att_work_interval[1], remain_interval[1])
    #                             if remain_interval and remain_interval[0] <= work_interval[1]:
    #                                 diff_intervals.append((remain_interval[0], work_interval[1]))
    #                             ac_sign_in = self._get_float_from_time(
    #                                 pytz.utc.localize(att_work_intervals[0][0]).astimezone(tz))
    #                             ac_sign_out = self._get_float_from_time(
    #                                 pytz.utc.localize(att_work_intervals[-1][1]).astimezone(tz))
    #                             # ac_sign_out = ac_sign_in + ((att_work_intervals[-1][1] - att_work_intervals[0][
    #                             #     0]).total_seconds() / 3600)
    #                         else:
    #                             late_in_interval = (work_interval[0], att_work_intervals[0][0])
    #                             overtime_interval = (work_interval[1], att_work_intervals[-1][1])
    #                             if overtime_interval[1] < overtime_interval[0]:
    #                                 overtime = timedelta(hours=0, minutes=0, seconds=0)
    #                                 diff_intervals.append((overtime_interval[1], overtime_interval[0]))
    #                             else:
    #                                 overtime = overtime_interval[1] - overtime_interval[0]
    #                             ac_sign_in = self._get_float_from_time(
    #                                 pytz.utc.localize(att_work_intervals[0][0]).astimezone(tz))
    #                             ac_sign_out = self._get_float_from_time(
    #                                 pytz.utc.localize(att_work_intervals[0][1]).astimezone(tz))
    #                             worked_hours = att_work_intervals[0][1] - att_work_intervals[0][0]
    #                             float_worked_hours = worked_hours.total_seconds() / 3600
    #                             # ac_sign_out = ac_sign_in + float_worked_hours
    #                     else:
    #                         late_in_interval = []
    #                         diff_intervals.append((work_interval[0], work_interval[1]))
    #                         if attendance_intervals:
    #                             ac_sign_in = self._get_float_from_time(
    #                                 pytz.utc.localize(attendance_intervals[0][0]).astimezone(tz))
    #                             ac_sign_out = self._get_float_from_time(
    #                                 pytz.utc.localize(attendance_intervals[-1][1]).astimezone(tz))
    #
    #                         status = "ab"
    #
    #                     if diff_intervals:
    #                         for diff_in in diff_intervals:
    #                             if leaves:
    #                                 status = "leave"
    #                                 diff_clean_intervals = calendar_id.att_interval_without_leaves(
    #                                     diff_in, leaves)
    #                                 for diff_clean in diff_clean_intervals:
    #                                     diff_time += diff_clean[1] - diff_clean[0]
    #                             else:
    #                                 diff_time += diff_in[1] - diff_in[0]
    #                     if late_in_interval:
    #                         if late_in_interval[1] < late_in_interval[0]:
    #                             late_in = timedelta(hours=0, minutes=0,
    #                                                 seconds=0)
    #                         else:
    #                             if leaves:
    #                                 late_clean_intervals = calendar_id.att_interval_without_leaves(
    #                                     late_in_interval, leaves)
    #                                 for late_clean in late_clean_intervals:
    #                                     late_in += late_clean[1] - late_clean[0]
    #                             else:
    #                                 late_in = late_in_interval[1] - late_in_interval[0]
    #                     float_overtime = overtime.total_seconds() / 3600
    #                     if float_overtime <= overtime_policy['wd_after']:
    #                         act_float_overtime = float_overtime = 0
    #                     else:
    #                         act_float_overtime = float_overtime
    #                         float_overtime = float_overtime * overtime_policy['wd_rate']
    #                     float_late = late_in.total_seconds() / 3600
    #                     act_float_late = late_in.total_seconds() / 3600
    #                     policy_late = policy_id.get_late(float_late)
    #                     float_diff = diff_time.total_seconds() / 3600
    #                     if status == 'ab':
    #                         if not abs_flag:
    #                             abs_cnt += 1
    #                         abs_flag = True
    #
    #                         act_float_diff = float_diff
    #                         float_diff = policy_id.get_absence(float_diff, abs_cnt)
    #                     else:
    #                         act_float_diff = float_diff
    #                         float_diff = policy_id.get_diff(float_diff)
    #                     values = {
    #                         'employee_id': emp.id,
    #                         'date': date,
    #                         'day': day_str,
    #                         'pl_sign_in': pl_sign_in,
    #                         'pl_sign_out': pl_sign_out,
    #                         'ac_sign_in': ac_sign_in,
    #                         'ac_sign_out': ac_sign_out,
    #                         'late_in': policy_late,
    #                         'act_late_in': act_float_late,
    #                         'overtime': float_overtime,
    #                         'act_overtime': act_float_overtime,
    #                         'diff_time': float_diff,
    #                         'act_diff_time': act_float_diff,
    #                         'status': status,
    #                         'note': leaves_note if status == 'leave' else '',
    #                         'manual_flag': manual_flag,
    #                         'manual_reason': manual_reason,
    #                         'punch_count': punch_count
    #                     }
    #                     if att_line_obj:
    #                         write_vals = {
    #                             'pl_sign_in': pl_sign_in,
    #                             'pl_sign_out': pl_sign_out,
    #                             'ac_sign_in': ac_sign_in,
    #                             'ac_sign_out': ac_sign_out,
    #                             'late_in': policy_late,
    #                             'act_late_in': act_float_late,
    #                             'overtime': float_overtime,
    #                             'act_overtime': act_float_overtime,
    #                             'diff_time': float_diff,
    #                             'act_diff_time': act_float_diff,
    #                             'status': status,
    #                             'worked_hours': 0,
    #                             'note': leaves_note if status == 'leave' else '',
    #                             'manual_flag': manual_flag,
    #                             'manual_reason': manual_reason,
    #                             'punch_count': punch_count
    #                         }
    #                         att_line_obj.write(write_vals)
    #                     else:
    #                         att_line.create(values)
    #
    #                     if hr_att:
    #                         hr_att.pl_sign_in = pl_sign_in
    #                         hr_att.pl_sign_out = pl_sign_out
    #                         hr_att.pl_sign_in_time = pl_sign_in_time2
    #                         hr_att.pl_sign_out_time = pl_sign_out_time2
    #                         hr_att.late_in = policy_late
    #                         hr_att.diff_time = float_diff
    #                         hr_att.act_late_in = act_float_late
    #                         hr_att.act_diff_time = act_float_diff
    #                         hr_att.overtime = float_overtime
    #                         hr_att.act_overtime = act_float_overtime
    #                     if hr_att1:
    #                         hr_att1.pl_sign_in = pl_sign_in
    #                         hr_att1.pl_sign_out = pl_sign_out
    #                         hr_att1.pl_sign_in_time = pl_sign_in_time2
    #                         hr_att1.pl_sign_out_time = pl_sign_out_time2
    #                         hr_att1.late_in = policy_late
    #                         hr_att1.diff_time = float_diff
    #                         hr_att1.act_late_in = act_float_late
    #                         hr_att1.act_diff_time = act_float_diff
    #                         hr_att1.overtime = float_overtime
    #                         hr_att1.act_overtime = act_float_overtime
    #
    #         # weekend process
    #         else:
    #             if attendance_intervals:
    #                 # print "thats weekend be over time "
    #                 for attendance_interval in attendance_intervals:
    #                     overtime = attendance_interval[1] - \
    #                                attendance_interval[0]
    #                     ac_sign_in = pytz.utc.localize(
    #                         attendance_interval[0]).astimezone(tz)
    #                     ac_sign_out = pytz.utc.localize(
    #                         attendance_interval[1]).astimezone(tz)
    #                     float_overtime = overtime.total_seconds() / 3600
    #                     if float_overtime <= overtime_policy['we_after']:
    #                         float_overtime = 0
    #                         act_float_overtime = 0
    #                     else:
    #                         act_float_overtime = float_overtime
    #                         float_overtime = act_float_overtime * \
    #                                          overtime_policy['we_rate']
    #                     ac_sign_in = pytz.utc.localize(
    #                         attendance_interval[0]).astimezone(tz)
    #                     ac_sign_out = pytz.utc.localize(
    #                         attendance_interval[1]).astimezone(tz)
    #                     worked_hours = attendance_interval[1] - \
    #                                    attendance_interval[0]
    #                     float_worked_hours = worked_hours.total_seconds() / 3600
    #                     values = {
    #                         'employee_id': emp.id,
    #                         'date': date,
    #                         'day': day_str,
    #                         'ac_sign_in': self._get_float_from_time(ac_sign_in),
    #                         'ac_sign_out': self._get_float_from_time(ac_sign_out),
    #                         'overtime': float_overtime,
    #                         'act_overtime': act_float_overtime,
    #                         'worked_hours': float_worked_hours,
    #                         'status': 'weekend',
    #                         'note': _("working in weekend"),
    #                         'manual_flag': manual_flag,
    #                         'manual_reason': manual_reason,
    #                         'punch_count': punch_count
    #                     }
    #                     if att_line_obj:
    #                         if att_line_obj.ovt_flag == '1' and float_overtime == 0:
    #                             float_overtime = float_worked_hours
    #                             act_float_overtime = float_worked_hours
    #
    #                         write_vals = {
    #                             'ac_sign_in': self._get_float_from_time(ac_sign_in),
    #                             'ac_sign_out': self._get_float_from_time(ac_sign_out),
    #                             'overtime': float_overtime,
    #                             'act_overtime': act_float_overtime,
    #                             'worked_hours': float_worked_hours,
    #                             'status': 'weekend',
    #                             'note': _("working in weekend"),
    #                             'pl_sign_in': 0,
    #                             'pl_sign_out': 0,
    #                             'late_in': 0,
    #                             'act_late_in': 0,
    #                             'diff_time': 0,
    #                             'act_diff_time': 0,
    #                             'manual_flag': manual_flag,
    #                             'manual_reason': manual_reason,
    #                             'punch_count': punch_count
    #                         }
    #                         att_line_obj.write(write_vals)
    #                     else:
    #                         att_line.create(values)
    #                     status = 'weekend'
    #                     if hr_att:
    #                         hr_att.overtime = float_overtime
    #                         hr_att.act_overtime = act_float_overtime
    #                     if hr_att1:
    #                         hr_att1.overtime = float_overtime
    #                         hr_att1.act_overtime = act_float_overtime
    #             else:
    #                 tmp_status = 'weekend'
    #                 tmp_note = ''
    #                 check_leave = self._check_hr_leave(emp.id, date)
    #                 if check_leave[0]:
    #                     tmp_status = 'leave'
    #                     tmp_note = check_leave[1]
    #
    #                 values = {
    #                     'employee_id': emp.id,
    #                     'date': date,
    #                     'day': day_str,
    #                     'status': tmp_status,
    #                     'note': tmp_note,
    #                 }
    #                 if att_line_obj:
    #                     write_vals = {
    #                         'pl_sign_in': 0,
    #                         'pl_sign_out': 0,
    #                         'worked_hours': 0,
    #                         'ac_sign_in': 0,
    #                         'ac_sign_out': 0,
    #                         'late_in': 0,
    #                         'act_late_in': 0,
    #                         'overtime': 0,
    #                         'act_overtime': 0,
    #                         'diff_time': 0,
    #                         'act_diff_time': 0,
    #                         'status': tmp_status,
    #                         'note': tmp_note,
    #                         'manual_flag': manual_flag,
    #                         'manual_reason': manual_reason,
    #                         'punch_count': punch_count
    #                     }
    #                     att_line_obj.write(write_vals)
    #                 else:
    #                     att_line.create(values)
    #                 status = 'weekend'
    #         if hr_att:
    #             hr_att.status = status
    #             hr_att.policy_process = '1'
    #         if hr_att1:
    #             hr_att1.status = status
    #             hr_att1.policy_process = '1'
    #
    #     return True

    def _check_hr_leave(self, emp_id=None, leave_date=None):
        leave_detail_obj = self.env['hr.leave.details'].sudo().search([('employee_id', '=', emp_id), ('leave_date', '=', leave_date), ('leave_id.state', '=', 'validate')], limit=1)
        #print(leave_detail_obj)
        if leave_detail_obj:
            des = leave_detail_obj.leave_id.name or ''
            return [True, des]
        else:
            return [False, '']

    def get_emp_shifting_schedule(self, date, emp):
        schedule_obj = emp.contract_id.resource_calendar_id

        shift_obj = self.env['shift.management.exchange.shift'].sudo().search([('employee_id', '=', emp.id), ('date', '=', date), ('state', '=', 'approve')], limit=1)
        if shift_obj:
            schedule_obj = shift_obj[0].resource_calendar_id
        else:
            shift_req_obj = self.env['shift.management.request'].sudo().search(
                [('employee_id', '=', emp.id), ('date_from', '<=', date), ('date_to', '>=', date), ('state', '=','approve')], order='date_from desc', limit=1)
            if shift_req_obj:
                schedule_obj = shift_req_obj[0].resource_calendar_id

        return schedule_obj

    def get_emp_shifting_schedule_data(self, employee, att_date, uatt_timestamp_tz):
        # ---------------------- over-ride-day (ORD) shift
        att_date_prev = att_date - timedelta(days=1)
        att_date_prev2 = att_date - timedelta(days=2)

        is_rostering_employee = employee.is_rostering_employee or False
        calendar_id_prev = employee.contract_id.resource_calendar_id or False
        calendar_id = employee.contract_id.resource_calendar_id or False
        if is_rostering_employee:
            calendar_id_prev = self.get_emp_shifting_schedule(att_date_prev, employee)
            calendar_id = self.get_emp_shifting_schedule(att_date, employee)

        is_over_ride_day_prev = False
        is_over_ride_day = False
        checkin_start_today = 0.0
        if calendar_id_prev:
            is_over_ride_day_prev = calendar_id_prev.is_over_ride_day
        if calendar_id:
            checkin_start_today = calendar_id.check_in_start

        #--------
        if is_over_ride_day_prev:
            checkout_end = checkin_start_today
            checkout_end_time = datetime.strptime(str(att_date), '%Y-%m-%d') + timedelta(
                hours=int(checkout_end), minutes=(checkout_end * 60) % 60, seconds=0)
            if uatt_timestamp_tz < checkout_end_time:
                att_date = att_date_prev
                calendar_id = calendar_id_prev

                calendar_id_prev = self.get_emp_shifting_schedule(att_date_prev2, employee)
                is_over_ride_day_prev = calendar_id_prev.is_over_ride_day

        if calendar_id:
            is_over_ride_day = calendar_id.is_over_ride_day

        return (att_date, calendar_id, is_over_ride_day, calendar_id_prev, is_over_ride_day_prev)