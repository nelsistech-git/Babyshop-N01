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
        ('6', 'Error-Invaid Date'),
        ('7', 'Error-Future Date')
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

        calendar_id = employee.contract_id.resource_calendar_id or False
        calendar_id_prev = employee.contract_id.resource_calendar_id or False

        is_rostering_employee = employee.is_rostering_employee or False
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
        if is_over_ride_day_prev: #this line can be commented
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
