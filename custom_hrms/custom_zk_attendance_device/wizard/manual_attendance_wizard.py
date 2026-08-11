import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime
from datetime import timedelta

_logger = logging.getLogger(__name__)


class ManualAttendanceWizard(models.TransientModel):
    _name = 'hr.manual.attendance.wizard'
    # _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Manual Attendance'

    # @api.model
    # def _set_domain_employee(self):
    #     if self.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
    #         return []
    #     else:
    #         return [('user_id.id', '=', self.env.user.id)]
    #
    # @api.model
    # def _def_employee(self):
    #
    #     emp_obj = self.env['hr.employee'].search([('user_id.id', '=', self.env.user.id)], limit=1)
    #     if emp_obj:
    #         return emp_obj[0].id
    #     else:
    #         return False

    @api.model
    def _get_current_date(self):
        """ :return current date """
        return fields.Date.today()

    # employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade', required=True,
    #                               default=lambda self: self._def_employee(),
    #                               domain=lambda self: self._set_domain_employee())

    device_id = fields.Many2one('attendance.device', string='Attendance Device', required=True)
    user_id = fields.Many2one('attendance.device.user', string='Device User', required=True)
    checkin_out_time = fields.Datetime(string='Timestamp', required=True)
    attendance_state_id = fields.Many2one('attendance.state', string='Attendance State',
                                          help='This technical field is to map the attendance'
                                               ' status stored in the device and the attendance status in Odoo',
                                          required=True)
    reason = fields.Text(string='Reason')

    # , default=lambda self: self._get_current_date()

    def action_submit_attendance(self):
        # current_date = datetime.date.today()
        current_datetime = datetime.datetime.now() + timedelta(hours=6)
        current_date2 = current_datetime.date()

        checkin_out_time = self.checkin_out_time
        device_id = self.device_id
        user_id = self.user_id
        attendance_state_id = self.attendance_state_id

        if checkin_out_time:
            checkin_out_time2 = checkin_out_time + timedelta(hours=6)
            checkin_out_date = datetime.datetime.strptime(str(checkin_out_time2), '%Y-%m-%d %H:%M:%S').strftime(
                '%Y-%m-%d')

            hr_manager = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')
            if not hr_manager:
                if checkin_out_date != str(current_date2):
                    raise UserError(_("Attendance must be today!"))
            else:
                if checkin_out_time2 > current_datetime:
                    raise UserError(_("Attendance cannot be given for upcoming days!"))

            user_attendance = self.env['user.attendance']
            user_attendance.create({'device_id': device_id.id,
                                    'user_id': user_id.id,
                                    'attendance_type': '20',
                                    'timestamp': checkin_out_time,
                                    'status': attendance_state_id.code,
                                    'attendance_state_id': attendance_state_id.id
                                    })
            # 'punch_type': '0',
            # 'punching_time': checkin_out_time,
            # 'address_id': None})

        return True

    # not used
    def action_manual_checkin(self):
        # current_date = datetime.date.today()
        current_datetime = datetime.datetime.now() + timedelta(hours=6)
        current_date2 = current_datetime.date()

        checkin_out_time = self.checkin_out_time
        employee_obj = self.employee_id
        if checkin_out_time:
            checkin_out_time2 = checkin_out_time + timedelta(hours=6)
            checkin_out_date = datetime.datetime.strptime(str(checkin_out_time2), '%Y-%m-%d %H:%M:%S').strftime(
                '%Y-%m-%d')
            if checkin_out_date != str(current_date2):
                raise UserError(_("Attendance must be today!"))
            else:
                zk_attendance = self.env['user.attendance']
                zk_attendance.create({'employee_id': employee_obj.id,
                                      # 'device_id': employee_obj.device_id,
                                      # 'type': '20',  # 20=Web
                                      })
                # 'punch_type': '0',
                # 'punching_time': checkin_out_time,
                # 'address_id': None})
        return True

    # not used
    def action_manual_checkout(self):
        # current_date = datetime.date.today()
        current_datetime = datetime.datetime.now() + timedelta(hours=6)
        current_date2 = current_datetime.date()

        checkin_out_time = self.checkin_out_time
        employee_obj = self.employee_id
        if checkin_out_time:
            checkin_out_time2 = checkin_out_time + timedelta(hours=6)

            checkin_out_date = datetime.datetime.strptime(str(checkin_out_time2), '%Y-%m-%d %H:%M:%S').strftime(
                '%Y-%m-%d')
            if checkin_out_date != str(current_date2):
                raise UserError(_("Attendance must be today!"))
            else:
                zk_attendance = self.env['user.attendance']
                zk_attendance.create({'employee_id': employee_obj.id,
                                      # 'device_id': employee_obj.device_id,
                                      # 'type': '20',  # 20=Web
                                      })
                # 'punch_type': '1',
                # 'punching_time': checkin_out_time,
                # 'address_id': None})
        return {}


class ManualAttendanceWizardEmployee(models.TransientModel):
    _name = 'hr.manual.attendance.wizard.employee'
    # _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Manual Attendance Employee'
    
    @api.model
    def _get_current_date(self):
        """ :return current date """
        return fields.Date.today()
    
    entry_type = fields.Selection(
        selection=[
            ("0", "One Employee One Date"),
            ("1", "Multiple Employee Multiple Date")
        ],
        string="Entry Type",
        default="0"
    )
    
    type = fields.Selection(
        selection=[
            ("in", "Check IN"),
            ("out", "Check OUT"),
            ("in-out", "Check IN-OUT")
        ],
        string="Type",
        default="in"
    )
    #----------- single entry
    employee_id = fields.Many2one('hr.employee', string='Employee')
    check_in_time = fields.Datetime(string='Check IN - Time')
    check_in_device_id = fields.Many2one('attendance.device', string='Check IN - Device')
    check_out_time = fields.Datetime(string='Check OUT - Time')
    check_out_device_id = fields.Many2one('attendance.device', string='Check OUT - Device')
    department_ids = fields.Many2many('hr.department', string='Department')
    #----------- multiple entry
    # employee_ids = fields.Many2many(comodel_name="hr.employee",
    #                            relation="hr_employee_manual_att_rel",
    #                            column1="manual_att_emp_col1",
    #                            column2="manual_att_emp_col2",
    #                            string="Employee(s)")
    
    employee_ids = fields.Many2many('hr.employee', string='Employee(s)')
    #config_ids = fields.Many2many('pos.config', 'remote_session_config_rel', 'wiz_id', 'config_id','POS config need to do', required=1)
    
    check_dt_from = fields.Date(string='Date From')
    check_dt_to = fields.Date(string='Date To')
    check_in_time_from = fields.Float(string='Check IN - Time (HH:MM)')
    check_out_time_to = fields.Float(string='Check OUT - Time (HH:MM)')
    #-----------
    reason = fields.Text(string='Reason')

    @api.onchange('department_ids')
    def _onchange_employees(self):
        domain = []
        if self.department_ids:
            domain += [('department_id', 'in', self.department_ids.ids)]

        if domain:
            emp_ids = self.env['hr.employee'].search(domain).ids
        else:
            emp_ids = None

        return {'domain': {'employee_ids': domain}, 'value': {'employee_ids': emp_ids}}
    
    def action_submit_attendance(self):
        entry_type = self.entry_type
        
        current_datetime = datetime.datetime.now() + timedelta(hours=6)
        current_date2 = current_datetime.date()
        type = self.type
        check_in_device_id = self.check_in_device_id
        check_out_device_id = self.check_out_device_id
        manual_uid = self.env.user.id or None
        manual_time = datetime.datetime.now()

        is_rostering_attendance_process = self.env['custom.common.settings'].search([('key', '=', 'is_rostering_attendance_process')], limit=1)
        is_upcoming_attendance_allow = self.env['custom.common.settings'].search([('key', '=', 'upcoming_date_attendance_allow')], limit=1)
        reason = self.reason
        if reason is None or reason == False:
            reason = ''
        
        synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)
        HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=synch_ignore_constraints)
        HrAttendance_obj = self.env['hr.attendance']

        if entry_type == '0':   
            employee = self.employee_id
            
            check_in_time = self.check_in_time
            check_out_time = self.check_out_time
            
            if type == 'in-out':
                if check_in_time and check_out_time:
                    if check_in_time < check_out_time:
                        check_in_time2 = check_in_time + timedelta(hours=6)
                        # check_in_date = datetime.datetime.strptime(str(check_in_time2), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                        check_in_date = check_in_time2.date()

                        check_out_time2 = check_out_time + timedelta(hours=6)
                        # check_out_date = datetime.datetime.strptime(str(check_out_time2), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                        check_out_date = check_out_time2.date()
                        # -------------- over-ride-day (ORD) shift
                        uatt_timestamp_tz = check_in_time2
                        data_list = HrAttendance_obj.get_emp_shifting_schedule_data(employee, check_in_date, uatt_timestamp_tz)
                        if len(data_list) == 5:
                            att_date = data_list[0]
                            calendar_id = data_list[1]
                            is_over_ride_day = data_list[2]
                            calendar_id_prev = data_list[3]
                            is_over_ride_day_prev = data_list[4]
                        else:
                            raise UserError(_("Contract to administrator for this issue!"))
                        #---------------

                        date_flag = False
                        if is_over_ride_day==False:
                            if check_in_date == check_out_date:
                                date_flag = True
                        else:
                            check_in_date2= check_in_date + timedelta(days=1)
                            if check_in_date2 == check_out_date or check_in_date == check_out_date:
                                date_flag = True

                        if date_flag:
                            hr_manager = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')
                            if not hr_manager:
                                if check_in_date != str(current_date2):
                                    raise UserError(_("Attendance must be today!"))
                                if check_out_date != str(current_date2):
                                    raise UserError(_("Attendance must be today!"))
                            else:
                                if not is_upcoming_attendance_allow.value:
                                    if check_in_time2 > current_datetime:
                                        raise UserError(_("Check-in cannot be given for upcoming days!"))
                                    if check_out_time2 > current_datetime:
                                        raise UserError(_("Check-out cannot be given for upcoming days!"))
    
                            #att_date = check_in_date

                            #synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)
                            #HrAttendance = self.env['hr.attendance'].with_context(ynch_ignore_constraints=synch_ignore_constraints)
                            hr_attendance = HrAttendance.search([('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
                            if hr_attendance:
                                manual_reason = ''
                                if hr_attendance.manual_reason == '':
                                    manual_reason = reason
                                else:
                                    manual_reason = str(hr_attendance.manual_reason) + '; ' + reason
    
                                punch_count = hr_attendance.punch_count

                                hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                    'check_in': check_in_time,
                                    'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                    'check_out': check_out_time,
                                    'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                    'manual_flag': 1,
                                    'manual_reason': manual_reason,
                                    'punch_count': punch_count + 2,
                                    'policy_process': '0',
                                    'pl_sign_in': 0,
                                    'pl_sign_out': 0,
                                    'late_in': 0,
                                    'late_in_abs': 0,
                                    'diff_time': 0,
                                    'act_late_in': 0,
                                    'act_diff_time': 0,
                                    'overtime': 0,
                                    'act_overtime': 0,
                                    'manual_uid': manual_uid,
                                    'manual_time': manual_time
                                })
                            else:
                                user_work_location_id = ''
                                if employee.user_work_location_id:
                                    user_work_location_id = employee.user_work_location_id.id
    
                                vals = {
                                    'employee_id': employee.id,
                                    'user_work_location_id': user_work_location_id,
                                    'attendance_date': att_date,
                                    'check_in': check_in_time,
                                    'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                    'check_out': check_out_time,
                                    'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                    'manual_flag': 1,
                                    'manual_reason': reason,
                                    'punch_count': 2,
                                    'manual_uid': manual_uid,
                                    'manual_time': manual_time,
                                    'resource_calendar_id': calendar_id.id,
                                    'is_over_ride_day': is_over_ride_day,
                                    'resource_calendar_id_prev': calendar_id_prev.id,
                                    'is_over_ride_day_prev': is_over_ride_day_prev
                                    # 'activity_id': attendance_activity.id,
                                }
                                try:
                                    hr_attendance = HrAttendance.create(vals)
                                except Exception as e:
                                    _logger.error(e)
    
                        else:
                            raise UserError(_("Check-IN and Check-OUT Date required Same date or 1 day diff for Over-Right-Day!"))
                    else:
                        raise UserError(_("Check-OUT time required greater than Check-IN time!"))
    
                else:
                    raise UserError(_("Required Check-IN, Check-OUT time!"))
            elif type == 'in':
                if check_in_time:
                    check_in_time2 = check_in_time + timedelta(hours=6)
                    check_in_date = check_in_time2.date()
                    check_out_time = check_in_time + timedelta(minutes=1)
    
                    hr_manager = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')
                    if not hr_manager:
                        if check_in_date != str(current_date2):
                            raise UserError(_("Attendance must be today!"))
                    else:
                        if not is_upcoming_attendance_allow.value:
                            if check_in_time2 > current_datetime:
                                raise UserError(_("Check-in cannot be given for upcoming days!"))
    
                    att_date = check_in_date

                    # -------------- over-ride-day (ORD) shift
                    uatt_timestamp_tz = check_in_time2
                    data_list = HrAttendance_obj.get_emp_shifting_schedule_data(employee, att_date, uatt_timestamp_tz)
                    if len(data_list) == 5:
                        att_date = data_list[0]
                        calendar_id = data_list[1]
                        is_over_ride_day = data_list[2]
                        calendar_id_prev = data_list[3]
                        is_over_ride_day_prev = data_list[4]
                    else:
                        raise UserError(_("Contract to administrator for this issue!"))
                    # -------------

                    #synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)
                    #HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=synch_ignore_constraints)
                    hr_attendance = HrAttendance.search(
                        [('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
                    if hr_attendance:
                        exist_check_out = hr_attendance.check_out
                        if check_in_time < exist_check_out:
                            manual_reason = ''
                            if hr_attendance.manual_reason == '':
                                manual_reason = reason
                            else:
                                manual_reason = str(hr_attendance.manual_reason) + '; ' + reason
    
                            punch_count = hr_attendance.punch_count
                            if punch_count == 1:
                                hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                    'check_in': check_in_time,
                                    'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                    'check_out': check_out_time,
                                    'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                    'manual_flag': 1,
                                    'manual_reason': manual_reason,
                                    'punch_count': punch_count,
                                    'policy_process': '0',
                                    'pl_sign_in': 0,
                                    'pl_sign_out': 0,
                                    'late_in': 0,
                                    'late_in_abs': 0,
                                    'diff_time': 0,
                                    'act_late_in': 0,
                                    'act_diff_time': 0,
                                    'overtime': 0,
                                    'act_overtime': 0,
                                    'manual_uid': manual_uid,
                                    'manual_time': manual_time
                                })
                            else:
                                hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                    'check_in': check_in_time,
                                    'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                    'manual_flag': 1,
                                    'manual_reason': manual_reason,
                                    'punch_count': punch_count + 1,
                                    'policy_process': '0',
                                    'pl_sign_in': 0,
                                    'pl_sign_out': 0,
                                    'late_in': 0,
                                    'late_in_abs': 0,
                                    'diff_time': 0,
                                    'act_late_in': 0,
                                    'act_diff_time': 0,
                                    'overtime': 0,
                                    'act_overtime': 0,
                                    'manual_uid': manual_uid,
                                    'manual_time': manual_time
                                })
                        else:
                            raise UserError(_("Check-IN time required less than Check-OUT time `%s`!") % (
                                    exist_check_out + timedelta(hours=6)))
                    else:
                        user_work_location_id = ''
                        if employee.user_work_location_id:
                            user_work_location_id = employee.user_work_location_id.id
    
                        vals = {
                            'employee_id': employee.id,
                            'user_work_location_id': user_work_location_id,
                            'attendance_date': att_date,
                            'check_in': check_in_time,
                            'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                            'check_out': check_out_time,
                            'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                            'manual_flag': 1,
                            'manual_reason': reason,
                            'punch_count': 1,
                            'manual_uid': manual_uid,
                            'manual_time': manual_time,
                            'resource_calendar_id': calendar_id.id,
                            'is_over_ride_day': is_over_ride_day,
                            'resource_calendar_id_prev': calendar_id_prev.id,
                            'is_over_ride_day_prev': is_over_ride_day_prev
                        }
                        try:
                            hr_attendance = HrAttendance.create(vals)
                        except Exception as e:
                            _logger.error(e)
                            print(e)

    
                else:
                    raise UserError(_("Required Check-IN time on the date!"))
    
            elif type == 'out':
                if check_out_time:
                    check_out_time2 = check_out_time + timedelta(hours=6)
                    check_out_date = check_out_time2.date()
    
                    hr_manager = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')
                    if not hr_manager:
                        if check_out_date != str(current_date2):
                            raise UserError(_("Attendance must be today!"))
                    else:
                        if check_out_time2 > current_datetime:
                            raise UserError(_("Check-out cannot be given for upcoming days!"))
    
                    att_date = check_out_date
                    # -------------- over-ride-day (ORD) shift
                    uatt_timestamp_tz = check_out_time2
                    data_list = HrAttendance_obj.get_emp_shifting_schedule_data(employee, att_date, uatt_timestamp_tz)
                    if len(data_list) == 5:
                        att_date = data_list[0]
                        calendar_id = data_list[1]
                        is_over_ride_day = data_list[2]
                        calendar_id_prev = data_list[3]
                        is_over_ride_day_prev = data_list[4]
                    else:
                        raise UserError(_("Contract to administrator for this issue!"))
                    #--------------------

                    #synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)
                    #HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=synch_ignore_constraints)
                    hr_attendance = HrAttendance.search([('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
                    if hr_attendance:
                        exist_check_in = hr_attendance.check_in
                        if check_out_time > exist_check_in:
                            manual_reason = ''
                            if hr_attendance.manual_reason == '':
                                manual_reason = reason
                            else:
                                manual_reason = str(hr_attendance.manual_reason) + '; ' + reason
    
                            punch_count = hr_attendance.punch_count
    
                            hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                'check_out': check_out_time,
                                'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                'manual_flag': 1,
                                'manual_reason': manual_reason,
                                'punch_count': punch_count + 1,
                                'policy_process': '0',
                                'pl_sign_in': 0,
                                'pl_sign_out': 0,
                                'late_in': 0,
                                'late_in_abs': 0,
                                'diff_time': 0,
                                'act_late_in': 0,
                                'act_diff_time': 0,
                                'overtime': 0,
                                'act_overtime': 0,
                                'manual_uid': manual_uid,
                                'manual_time': manual_time
                            })
                        else:
                            raise UserError(_("Check-OUT time required greater than Check-IN time `%s`!") % (
                                    exist_check_in + timedelta(hours=6)))
    
                    else:
                        raise UserError(_("Required Check-IN first on the date!"))
                else:
                    raise UserError(_("Required Check-OUT time on the date!"))
    
            return True
        
        elif entry_type == '1':
            employee_ids = self.employee_ids
            check_dt_from = self.check_dt_from
            check_dt_to = self.check_dt_to
            in_time_from = self.check_in_time_from
            out_time_to = self.check_out_time_to
                
            if check_dt_from > check_dt_to:
                raise UserError(_("From-Date can not be greater than To-Date!"))
            else:
                pass
            
            hr_manager = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')
            if not hr_manager:
                if check_dt_from != str(current_date2):
                    raise UserError(_("Attendance must be today!"))
                elif check_dt_to != str(current_date2):
                    raise UserError(_("Attendance must be today!"))
            else:
                if check_dt_to > current_date2:
                    raise UserError(_("Check-in can not be given for upcoming days!"))
            
            # try:
            #     checkout_end_time = datetime.strptime(str(att_date), '%Y-%m-%d') + timedelta(
            #         hours=int(checkout_end_prev), minutes=(checkout_end_prev * 60) % 60, seconds=0)
            #     in_spit = str(in_time_from).split('.')
            #     in_hours = int(in_spit[0])
            #     in_minutes = int(in_spit[1])
            # except:
            #     in_hours = 0
            #     in_minutes = 0
            # try:
            #     out_spit = str(out_time_to).split('.')
            #     out_hours = int(out_spit[0])
            #     out_minutes = int(out_spit[1])
            # except:
            #     out_hours = 0
            #     out_minutes = 0

            try:
                in_time_from_formatted = timedelta(hours=int(in_time_from), minutes=(in_time_from * 60) % 60, seconds=0)
            except:
                in_time_from_formatted = 0.0

            try:
                out_time_to_formatted = timedelta(hours=int(out_time_to), minutes=(out_time_to * 60) % 60, seconds=0)
            except:
                out_time_to_formatted = 0.0

            all_dates = [(check_dt_from + timedelta(days=x)) for x in range((check_dt_to - check_dt_from).days + 1)]
            #---------------  
            for employee in employee_ids:                
                for day in all_dates:
                    #check_in_time = datetime.datetime.strptime(str(day),'%Y-%m-%d') + timedelta(hours=in_hours, minutes=in_minutes, seconds=0)
                    check_in_time = datetime.datetime.strptime(str(day),'%Y-%m-%d') + in_time_from_formatted
                    check_in_time1 = check_in_time - timedelta(hours=6)

                    #check_out_time = datetime.datetime.strptime(str(day),'%Y-%m-%d') + timedelta(hours=out_hours, minutes=out_minutes, seconds=0)
                    #-------need to chk over-right-day here for day
                    # -------------- over-ride-day (ORD) shift
                    if type == 'out':
                        check_out_time = datetime.datetime.strptime(str(day), '%Y-%m-%d') + out_time_to_formatted
                        uatt_timestamp_tz1 = check_out_time
                        data_list1 = HrAttendance_obj.get_emp_shifting_schedule_data(employee, check_out_time.date(),
                                                                                     uatt_timestamp_tz1)
                    else:
                        uatt_timestamp_tz1 = check_in_time
                        data_list1 = HrAttendance_obj.get_emp_shifting_schedule_data(employee, check_in_time.date(), uatt_timestamp_tz1)

                    if len(data_list1) == 5:
                        is_over_ride_day = data_list1[2]
                    else:
                        raise UserError(_("Contract to administrator for this issue!"))
                    # ---------------
                    if is_over_ride_day:
                        day= day+timedelta(days=1)

                    check_out_time = datetime.datetime.strptime(str(day),'%Y-%m-%d') + out_time_to_formatted
                    check_out_time1 = check_out_time - timedelta(hours=6)
                    
                    if type == 'in-out':
                        if check_in_time and check_out_time:
                            if check_in_time < check_out_time:
                                check_in_date = check_in_time.date()
                                check_out_date = check_out_time.date()
                                # -------------- over-ride-day (ORD) shift
                                uatt_timestamp_tz = check_in_time
                                data_list = HrAttendance_obj.get_emp_shifting_schedule_data(employee, check_in_date, uatt_timestamp_tz)
                                if len(data_list) == 5:
                                    att_date = data_list[0]
                                    calendar_id = data_list[1]
                                    is_over_ride_day = data_list[2]
                                    calendar_id_prev = data_list[3]
                                    is_over_ride_day_prev = data_list[4]
                                else:
                                    raise UserError(_("Contract to administrator for this issue!"))
                                # ---------------

                                date_flag = False
                                if is_over_ride_day == False:
                                    if check_in_date == check_out_date:
                                        date_flag = True
                                else:
                                    check_in_date2 = check_in_date + timedelta(days=1)
                                    if check_in_date2 == check_out_date or check_in_date == check_out_date:
                                        date_flag = True

                                if date_flag:
                                    #att_date = check_in_date
                                    
                                    hr_attendance = HrAttendance.search([('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
                                    if hr_attendance:
                                        manual_reason = ''
                                        if hr_attendance.manual_reason == '':
                                            manual_reason = reason
                                        else:
                                            manual_reason = str(hr_attendance.manual_reason) + '; ' + reason
            
                                        punch_count = hr_attendance.punch_count
            
                                        hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                            'check_in': check_in_time1,
                                            'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                            'check_out': check_out_time1,
                                            'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                            'manual_flag': 1,
                                            'manual_reason': manual_reason,
                                            'punch_count': punch_count + 2,
                                            'policy_process': '0',
                                            'pl_sign_in': 0,
                                            'pl_sign_out': 0,
                                            'late_in': 0,
                                            'late_in_abs': 0,
                                            'diff_time': 0,
                                            'act_late_in': 0,
                                            'act_diff_time': 0,
                                            'overtime': 0,
                                            'act_overtime': 0,
                                            'manual_uid': manual_uid,
                                            'manual_time': manual_time
                                        })
                                    else:
                                        user_work_location_id = ''
                                        if employee.user_work_location_id:
                                            user_work_location_id = employee.user_work_location_id.id
            
                                        vals = {
                                            'employee_id': employee.id,
                                            'user_work_location_id': user_work_location_id,
                                            'attendance_date': att_date,
                                            'check_in': check_in_time1,
                                            'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                            'check_out': check_out_time1,
                                            'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                            'manual_flag': 1,
                                            'manual_reason': reason,
                                            'punch_count': 2,
                                            'manual_uid': manual_uid,
                                            'manual_time': manual_time,
                                            'resource_calendar_id': calendar_id.id,
                                            'is_over_ride_day': is_over_ride_day,
                                            'resource_calendar_id_prev': calendar_id_prev.id,
                                            'is_over_ride_day_prev': is_over_ride_day_prev
                                            # 'activity_id': attendance_activity.id,
                                        }
                                        try:
                                            hr_attendance = HrAttendance.create(vals)
                                        except Exception as e:
                                            _logger.error(e)
            
                                else:
                                    raise UserError(_("Check-IN and Check-OUT Date required Same date or 1 day diff for Over-Right-Day!"))
                            else:
                                raise UserError(_("Check-OUT time can not less than Check-IN time!"))
            
                        else:
                            raise UserError(_("Required Check-IN, Check-OUT time!"))
                    elif type == 'in':
                        if check_in_time:
                            check_in_date = check_in_time.date()
                            check_out_time = check_in_time + timedelta(minutes=1)          
                            
                            check_out_time1 = check_out_time - timedelta(hours=6)
                                              
                            att_date = check_in_date
                            # -------------- over-ride-day (ORD) shift
                            uatt_timestamp_tz = check_in_time
                            data_list = HrAttendance_obj.get_emp_shifting_schedule_data(employee, att_date, uatt_timestamp_tz)
                            if len(data_list) == 5:
                                att_date = data_list[0]
                                calendar_id = data_list[1]
                                is_over_ride_day = data_list[2]
                                calendar_id_prev = data_list[3]
                                is_over_ride_day_prev = data_list[4]
                            else:
                                raise UserError(_("Contract to administrator for this issue!"))
                            # -------------

                            hr_attendance = HrAttendance.search([('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
                            if hr_attendance:
                                exist_check_out = hr_attendance.check_out
                                if check_in_time1 < exist_check_out:
                                    manual_reason = ''
                                    if hr_attendance.manual_reason == '':
                                        manual_reason = reason
                                    else:
                                        manual_reason = str(hr_attendance.manual_reason) + '; ' + reason
            
                                    punch_count = hr_attendance.punch_count
                                    if punch_count == 1:
                                        hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                            'check_in': check_in_time1,
                                            'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                            'check_out': check_out_time1,
                                            'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                            'manual_flag': 1,
                                            'manual_reason': manual_reason,
                                            'punch_count': punch_count,
                                            'policy_process': '0',
                                            'pl_sign_in': 0,
                                            'pl_sign_out': 0,
                                            'late_in': 0,
                                            'late_in_abs': 0,
                                            'diff_time': 0,
                                            'act_late_in': 0,
                                            'act_diff_time': 0,
                                            'overtime': 0,
                                            'act_overtime': 0,
                                            'manual_uid': manual_uid,
                                            'manual_time': manual_time
                                        })
                                    else:
                                        hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                            'check_in': check_in_time1,
                                            'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                            'manual_flag': 1,
                                            'manual_reason': manual_reason,
                                            'punch_count': punch_count + 1,
                                            'policy_process': '0',
                                            'pl_sign_in': 0,
                                            'pl_sign_out': 0,
                                            'late_in': 0,
                                            'late_in_abs': 0,
                                            'diff_time': 0,
                                            'act_late_in': 0,
                                            'act_diff_time': 0,
                                            'overtime': 0,
                                            'act_overtime': 0,
                                            'manual_uid': manual_uid,
                                            'manual_time': manual_time
                                        })
                                else:
                                    raise UserError(_("Check-IN time required less than Check-OUT time `%s`!") % (exist_check_out + timedelta(hours=6)))
                            else:
                                user_work_location_id = ''
                                if employee.user_work_location_id:
                                    user_work_location_id = employee.user_work_location_id.id
            
                                vals = {
                                    'employee_id': employee.id,
                                    'user_work_location_id': user_work_location_id,
                                    'attendance_date': att_date,
                                    'check_in': check_in_time1,
                                    'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                    'check_out': check_out_time1,
                                    'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                    'manual_flag': 1,
                                    'manual_reason': reason,
                                    'punch_count': 1,
                                    'manual_uid': manual_uid,
                                    'manual_time': manual_time,
                                    'resource_calendar_id': calendar_id.id,
                                    'is_over_ride_day': is_over_ride_day,
                                    'resource_calendar_id_prev': calendar_id_prev.id,
                                    'is_over_ride_day_prev': is_over_ride_day_prev
                                }
                                try:
                                    hr_attendance = HrAttendance.create(vals)
                                except Exception as e:
                                    _logger.error(e)
                        else:
                            raise UserError(_("Required Check-IN time on the date!"))
                            
                    elif type == 'out':
                        if check_out_time:
                            check_out_date = check_out_time.date()                            
                            att_date = check_out_date
                            # -------------- over-ride-day (ORD) shift
                            uatt_timestamp_tz = check_out_time
                            data_list = HrAttendance_obj.get_emp_shifting_schedule_data(employee, att_date, uatt_timestamp_tz)
                            if len(data_list) == 5:
                                att_date = data_list[0]
                            else:
                                raise UserError(_("Contract to administrator for this issue!"))
                            # -------------

                            hr_attendance = HrAttendance.search([('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
                            if hr_attendance:
                                exist_check_in = hr_attendance.check_in
                                if check_out_time1 > exist_check_in:
                                    manual_reason = ''
                                    if hr_attendance.manual_reason == '':
                                        manual_reason = reason
                                    else:
                                        manual_reason = str(hr_attendance.manual_reason) + '; ' + reason
                                        
                                    punch_count = hr_attendance.punch_count
                                    hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                        'check_out': check_out_time1,
                                        'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                        'manual_flag': 1,
                                        'manual_reason': manual_reason,
                                        'punch_count': punch_count + 1,
                                        'policy_process': '0',
                                        'pl_sign_in': 0,
                                        'pl_sign_out': 0,
                                        'late_in': 0,
                                        'late_in_abs': 0,
                                        'diff_time': 0,
                                        'act_late_in': 0,
                                        'act_diff_time': 0,
                                        'overtime': 0,
                                        'act_overtime': 0,
                                        'manual_uid': manual_uid,
                                        'manual_time': manual_time
                                    })
                                else:
                                    raise UserError(_("Check-OUT time required greater than Check-IN time `%s`!") % (
                                            exist_check_in + timedelta(hours=6)))
            
                            else:
                                raise UserError(_("Required Check-IN first on the date!"))
                        else:
                            raise UserError(_("Required Check-OUT time on the date!"))
                
            return True

    def x_action_submit_attendance(self):
        entry_type = self.entry_type

        current_datetime = datetime.datetime.now() + timedelta(hours=6)
        current_date2 = current_datetime.date()
        type = self.type
        check_in_device_id = self.check_in_device_id
        check_out_device_id = self.check_out_device_id
        manual_uid = self.env.user.id or None
        manual_time = datetime.datetime.now()

        is_rostering_attendance_process = self.env['custom.common.settings'].search(
            [('key', '=', 'is_rostering_attendance_process')], limit=1)
        is_upcoming_attendance_allow = self.env['custom.common.settings'].search(
            [('key', '=', 'upcoming_date_attendance_allow')], limit=1)
        reason = self.reason
        if reason is None or reason == False:
            reason = ''

        synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)
        HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=synch_ignore_constraints)

        if entry_type == '0':
            employee = self.employee_id

            check_in_time = self.check_in_time
            check_out_time = self.check_out_time

            if type == 'in-out':
                if check_in_time and check_out_time:
                    if check_in_time < check_out_time:
                        check_in_time2 = check_in_time + timedelta(hours=6)
                        # check_in_date = datetime.datetime.strptime(str(check_in_time2), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                        check_in_date = check_in_time2.date()

                        check_out_time2 = check_out_time + timedelta(hours=6)
                        # check_out_date = datetime.datetime.strptime(str(check_out_time2), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                        check_out_date = check_out_time2.date()
                        if check_in_date == check_out_date:

                            hr_manager = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')
                            if not hr_manager:
                                if check_in_date != str(current_date2):
                                    raise UserError(_("Attendance must be today!"))
                                if check_out_date != str(current_date2):
                                    raise UserError(_("Attendance must be today!"))
                            else:
                                if not is_upcoming_attendance_allow.value:
                                    if check_in_time2 > current_datetime:
                                        raise UserError(_("Check-in cannot be given for upcoming days!"))
                                    if check_out_time2 > current_datetime:
                                        raise UserError(_("Check-out cannot be given for upcoming days!"))

                            att_date = check_in_date
                            # synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)
                            # HrAttendance = self.env['hr.attendance'].with_context(ynch_ignore_constraints=synch_ignore_constraints)
                            hr_attendance = HrAttendance.search(
                                [('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
                            if hr_attendance:
                                manual_reason = ''
                                if hr_attendance.manual_reason == '':
                                    manual_reason = reason
                                else:
                                    manual_reason = str(hr_attendance.manual_reason) + '; ' + reason

                                punch_count = hr_attendance.punch_count

                                hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                    'check_in': check_in_time,
                                    'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                    'check_out': check_out_time,
                                    'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                    'manual_flag': 1,
                                    'manual_reason': manual_reason,
                                    'punch_count': punch_count + 2,
                                    'policy_process': '0',
                                    'pl_sign_in': 0,
                                    'pl_sign_out': 0,
                                    'late_in': 0,
                                    'late_in_abs': 0,
                                    'diff_time': 0,
                                    'act_late_in': 0,
                                    'act_diff_time': 0,
                                    'overtime': 0,
                                    'act_overtime': 0,
                                    'manual_uid': manual_uid,
                                    'manual_time': manual_time
                                })
                            else:
                                user_work_location_id = ''
                                if employee.user_work_location_id:
                                    user_work_location_id = employee.user_work_location_id.id

                                vals = {
                                    'employee_id': employee.id,
                                    'user_work_location_id': user_work_location_id,
                                    'attendance_date': att_date,
                                    'check_in': check_in_time,
                                    'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                    'check_out': check_out_time,
                                    'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                    'manual_flag': 1,
                                    'manual_reason': reason,
                                    'punch_count': 2,
                                    'manual_uid': manual_uid,
                                    'manual_time': manual_time
                                    # 'activity_id': attendance_activity.id,
                                }
                                try:
                                    hr_attendance = HrAttendance.create(vals)
                                except Exception as e:
                                    _logger.error(e)

                        else:
                            raise UserError(_("Check-IN and Check-OUT Date required Same date!"))
                    else:
                        raise UserError(_("Check-OUT time required greater than Check-IN time!"))

                else:
                    raise UserError(_("Required Check-IN, Check-OUT time!"))
            elif type == 'in':
                if check_in_time:
                    check_in_time2 = check_in_time + timedelta(hours=6)
                    check_in_date = check_in_time2.date()
                    check_out_time = check_in_time + timedelta(minutes=1)

                    hr_manager = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')
                    if not hr_manager:
                        if check_in_date != str(current_date2):
                            raise UserError(_("Attendance must be today!"))
                    else:
                        if not is_upcoming_attendance_allow.value:
                            if check_in_time2 > current_datetime:
                                raise UserError(_("Check-in cannot be given for upcoming days!"))

                    att_date = check_in_date
                    # synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)
                    # HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=synch_ignore_constraints)
                    hr_attendance = HrAttendance.search(
                        [('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
                    if hr_attendance:
                        exist_check_out = hr_attendance.check_out
                        if check_in_time < exist_check_out:
                            manual_reason = ''
                            if hr_attendance.manual_reason == '':
                                manual_reason = reason
                            else:
                                manual_reason = str(hr_attendance.manual_reason) + '; ' + reason

                            punch_count = hr_attendance.punch_count
                            if punch_count == 1:
                                hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                    'check_in': check_in_time,
                                    'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                    'check_out': check_out_time,
                                    'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                    'manual_flag': 1,
                                    'manual_reason': manual_reason,
                                    'punch_count': punch_count,
                                    'policy_process': '0',
                                    'pl_sign_in': 0,
                                    'pl_sign_out': 0,
                                    'late_in': 0,
                                    'late_in_abs': 0,
                                    'diff_time': 0,
                                    'act_late_in': 0,
                                    'act_diff_time': 0,
                                    'overtime': 0,
                                    'act_overtime': 0,
                                    'manual_uid': manual_uid,
                                    'manual_time': manual_time
                                })
                            else:
                                hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                    'check_in': check_in_time,
                                    'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                    'manual_flag': 1,
                                    'manual_reason': manual_reason,
                                    'punch_count': punch_count + 1,
                                    'policy_process': '0',
                                    'pl_sign_in': 0,
                                    'pl_sign_out': 0,
                                    'late_in': 0,
                                    'late_in_abs': 0,
                                    'diff_time': 0,
                                    'act_late_in': 0,
                                    'act_diff_time': 0,
                                    'overtime': 0,
                                    'act_overtime': 0,
                                    'manual_uid': manual_uid,
                                    'manual_time': manual_time
                                })
                        else:
                            raise UserError(_("Check-IN time required less than Check-OUT time `%s`!") % (
                                    exist_check_out + timedelta(hours=6)))
                    else:
                        user_work_location_id = ''
                        if employee.user_work_location_id:
                            user_work_location_id = employee.user_work_location_id.id

                        vals = {
                            'employee_id': employee.id,
                            'user_work_location_id': user_work_location_id,
                            'attendance_date': att_date,
                            'check_in': check_in_time,
                            'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                            'check_out': check_out_time,
                            'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                            'manual_flag': 1,
                            'manual_reason': reason,
                            'punch_count': 1,
                            'manual_uid': manual_uid,
                            'manual_time': manual_time
                        }
                        try:
                            hr_attendance = HrAttendance.create(vals)
                        except Exception as e:
                            _logger.error(e)
                            print(e)


                else:
                    raise UserError(_("Required Check-IN time on the date!"))

            elif type == 'out':
                if check_out_time:
                    check_out_time2 = check_out_time + timedelta(hours=6)
                    check_out_date = check_out_time2.date()

                    hr_manager = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')
                    if not hr_manager:
                        if check_out_date != str(current_date2):
                            raise UserError(_("Attendance must be today!"))
                    else:
                        if check_out_time2 > current_datetime:
                            raise UserError(_("Check-out cannot be given for upcoming days!"))

                    att_date = check_out_date
                    # synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)
                    # HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=synch_ignore_constraints)
                    hr_attendance = HrAttendance.search(
                        [('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
                    if hr_attendance:
                        exist_check_in = hr_attendance.check_in
                        if check_out_time > exist_check_in:
                            manual_reason = ''
                            if hr_attendance.manual_reason == '':
                                manual_reason = reason
                            else:
                                manual_reason = str(hr_attendance.manual_reason) + '; ' + reason

                            punch_count = hr_attendance.punch_count

                            hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                'check_out': check_out_time,
                                'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                'manual_flag': 1,
                                'manual_reason': manual_reason,
                                'punch_count': punch_count + 1,
                                'policy_process': '0',
                                'pl_sign_in': 0,
                                'pl_sign_out': 0,
                                'late_in': 0,
                                'late_in_abs': 0,
                                'diff_time': 0,
                                'act_late_in': 0,
                                'act_diff_time': 0,
                                'overtime': 0,
                                'act_overtime': 0,
                                'manual_uid': manual_uid,
                                'manual_time': manual_time
                            })
                        else:
                            raise UserError(_("Check-OUT time required greater than Check-IN time `%s`!") % (
                                    exist_check_in + timedelta(hours=6)))

                    else:
                        raise UserError(_("Required Check-IN first on the date!"))
                else:
                    raise UserError(_("Required Check-OUT time on the date!"))

            return True

        elif entry_type == '1':
            employee_ids = self.employee_ids
            check_dt_from = self.check_dt_from
            check_dt_to = self.check_dt_to
            in_time_from = self.check_in_time_from
            out_time_to = self.check_out_time_to

            if check_dt_from > check_dt_to:
                raise UserError(_("From-Date can not be greater than To-Date!"))
            else:
                pass

            hr_manager = self.env.user.has_group('hr_attendance.group_hr_attendance_manager')
            if not hr_manager:
                if check_dt_from != str(current_date2):
                    raise UserError(_("Attendance must be today!"))
                elif check_dt_to != str(current_date2):
                    raise UserError(_("Attendance must be today!"))
            else:
                if check_dt_to > current_date2:
                    raise UserError(_("Check-in can not be given for upcoming days!"))

            # try:
            #     checkout_end_time = datetime.strptime(str(att_date), '%Y-%m-%d') + timedelta(
            #         hours=int(checkout_end_prev), minutes=(checkout_end_prev * 60) % 60, seconds=0)
            #     in_spit = str(in_time_from).split('.')
            #     in_hours = int(in_spit[0])
            #     in_minutes = int(in_spit[1])
            # except:
            #     in_hours = 0
            #     in_minutes = 0
            # try:
            #     out_spit = str(out_time_to).split('.')
            #     out_hours = int(out_spit[0])
            #     out_minutes = int(out_spit[1])
            # except:
            #     out_hours = 0
            #     out_minutes = 0

            try:
                in_time_from_formatted = timedelta(hours=int(in_time_from), minutes=(in_time_from * 60) % 60, seconds=0)
            except:
                in_time_from_formatted = 0.0

            try:
                out_time_to_formatted = timedelta(hours=int(out_time_to), minutes=(out_time_to * 60) % 60, seconds=0)
            except:
                out_time_to_formatted = 0.0

            all_dates = [(check_dt_from + timedelta(days=x)) for x in range((check_dt_to - check_dt_from).days + 1)]
            # ---------------
            for employee in employee_ids:
                for day in all_dates:
                    # check_in_time = datetime.datetime.strptime(str(day),'%Y-%m-%d') + timedelta(hours=in_hours, minutes=in_minutes, seconds=0)
                    check_in_time = datetime.datetime.strptime(str(day), '%Y-%m-%d') + in_time_from_formatted
                    # check_out_time = datetime.datetime.strptime(str(day),'%Y-%m-%d') + timedelta(hours=out_hours, minutes=out_minutes, seconds=0)
                    # -------need to chk over-right-day here for day
                    check_out_time = datetime.datetime.strptime(str(day), '%Y-%m-%d') + out_time_to_formatted

                    check_in_time1 = check_in_time - timedelta(hours=6)
                    check_out_time1 = check_out_time - timedelta(hours=6)

                    if type == 'in-out':
                        if check_in_time and check_out_time:
                            if check_in_time < check_out_time:
                                check_in_date = check_in_time.date()
                                check_out_date = check_out_time.date()
                                if check_in_date == check_out_date:
                                    att_date = check_in_date

                                    hr_attendance = HrAttendance.search(
                                        [('employee_id', '=', employee.id), ('attendance_date', '=', att_date)],
                                        limit=1)
                                    if hr_attendance:
                                        manual_reason = ''
                                        if hr_attendance.manual_reason == '':
                                            manual_reason = reason
                                        else:
                                            manual_reason = str(hr_attendance.manual_reason) + '; ' + reason

                                        punch_count = hr_attendance.punch_count

                                        hr_attendance.with_context(
                                            synch_ignore_constraints=synch_ignore_constraints).write({
                                            'check_in': check_in_time1,
                                            'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                            'check_out': check_out_time1,
                                            'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                            'manual_flag': 1,
                                            'manual_reason': manual_reason,
                                            'punch_count': punch_count + 2,
                                            'policy_process': '0',
                                            'pl_sign_in': 0,
                                            'pl_sign_out': 0,
                                            'late_in': 0,
                                            'late_in_abs': 0,
                                            'diff_time': 0,
                                            'act_late_in': 0,
                                            'act_diff_time': 0,
                                            'overtime': 0,
                                            'act_overtime': 0,
                                            'manual_uid': manual_uid,
                                            'manual_time': manual_time
                                        })
                                    else:
                                        user_work_location_id = ''
                                        if employee.user_work_location_id:
                                            user_work_location_id = employee.user_work_location_id.id

                                        vals = {
                                            'employee_id': employee.id,
                                            'user_work_location_id': user_work_location_id,
                                            'attendance_date': att_date,
                                            'check_in': check_in_time1,
                                            'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                            'check_out': check_out_time1,
                                            'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                            'manual_flag': 1,
                                            'manual_reason': reason,
                                            'punch_count': 2,
                                            'manual_uid': manual_uid,
                                            'manual_time': manual_time
                                            # 'activity_id': attendance_activity.id,
                                        }
                                        try:
                                            hr_attendance = HrAttendance.create(vals)
                                        except Exception as e:
                                            _logger.error(e)

                                else:
                                    raise UserError(_("Check-IN and Check-OUT Date required Same date!"))
                            else:
                                raise UserError(_("Check-OUT time can not less than Check-IN time!"))

                        else:
                            raise UserError(_("Required Check-IN, Check-OUT time!"))
                    elif type == 'in':
                        if check_in_time:
                            check_in_date = check_in_time.date()
                            check_out_time = check_in_time + timedelta(minutes=1)

                            check_out_time1 = check_out_time - timedelta(hours=6)

                            att_date = check_in_date
                            hr_attendance = HrAttendance.search(
                                [('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
                            if hr_attendance:
                                exist_check_out = hr_attendance.check_out
                                if check_in_time1 < exist_check_out:
                                    manual_reason = ''
                                    if hr_attendance.manual_reason == '':
                                        manual_reason = reason
                                    else:
                                        manual_reason = str(hr_attendance.manual_reason) + '; ' + reason

                                    punch_count = hr_attendance.punch_count
                                    if punch_count == 1:
                                        hr_attendance.with_context(
                                            synch_ignore_constraints=synch_ignore_constraints).write({
                                            'check_in': check_in_time1,
                                            'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                            'check_out': check_out_time1,
                                            'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                            'manual_flag': 1,
                                            'manual_reason': manual_reason,
                                            'punch_count': punch_count,
                                            'policy_process': '0',
                                            'pl_sign_in': 0,
                                            'pl_sign_out': 0,
                                            'late_in': 0,
                                            'late_in_abs': 0,
                                            'diff_time': 0,
                                            'act_late_in': 0,
                                            'act_diff_time': 0,
                                            'overtime': 0,
                                            'act_overtime': 0,
                                            'manual_uid': manual_uid,
                                            'manual_time': manual_time
                                        })
                                    else:
                                        hr_attendance.with_context(
                                            synch_ignore_constraints=synch_ignore_constraints).write({
                                            'check_in': check_in_time1,
                                            'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                            'manual_flag': 1,
                                            'manual_reason': manual_reason,
                                            'punch_count': punch_count + 1,
                                            'policy_process': '0',
                                            'pl_sign_in': 0,
                                            'pl_sign_out': 0,
                                            'late_in': 0,
                                            'late_in_abs': 0,
                                            'diff_time': 0,
                                            'act_late_in': 0,
                                            'act_diff_time': 0,
                                            'overtime': 0,
                                            'act_overtime': 0,
                                            'manual_uid': manual_uid,
                                            'manual_time': manual_time
                                        })
                                else:
                                    raise UserError(_("Check-IN time required less than Check-OUT time `%s`!") % (
                                                exist_check_out + timedelta(hours=6)))
                            else:
                                user_work_location_id = ''
                                if employee.user_work_location_id:
                                    user_work_location_id = employee.user_work_location_id.id

                                vals = {
                                    'employee_id': employee.id,
                                    'user_work_location_id': user_work_location_id,
                                    'attendance_date': att_date,
                                    'check_in': check_in_time1,
                                    'checkin_device_id': check_in_device_id.id if check_in_device_id else None,
                                    'check_out': check_out_time1,
                                    'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                    'manual_flag': 1,
                                    'manual_reason': reason,
                                    'punch_count': 1,
                                    'manual_uid': manual_uid,
                                    'manual_time': manual_time
                                }
                                try:
                                    hr_attendance = HrAttendance.create(vals)
                                except Exception as e:
                                    _logger.error(e)
                        else:
                            raise UserError(_("Required Check-IN time on the date!"))

                    elif type == 'out':
                        if check_out_time:
                            check_out_date = check_out_time.date()
                            att_date = check_out_date
                            hr_attendance = HrAttendance.search(
                                [('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
                            if hr_attendance:
                                exist_check_in = hr_attendance.check_in
                                if check_out_time1 > exist_check_in:
                                    manual_reason = ''
                                    if hr_attendance.manual_reason == '':
                                        manual_reason = reason
                                    else:
                                        manual_reason = str(hr_attendance.manual_reason) + '; ' + reason

                                    punch_count = hr_attendance.punch_count
                                    hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write(
                                        {
                                            'check_out': check_out_time1,
                                            'checkout_device_id': check_out_device_id.id if check_out_device_id else None,
                                            'manual_flag': 1,
                                            'manual_reason': manual_reason,
                                            'punch_count': punch_count + 1,
                                            'policy_process': '0',
                                            'pl_sign_in': 0,
                                            'pl_sign_out': 0,
                                            'late_in': 0,
                                            'late_in_abs': 0,
                                            'diff_time': 0,
                                            'act_late_in': 0,
                                            'act_diff_time': 0,
                                            'overtime': 0,
                                            'act_overtime': 0,
                                            'manual_uid': manual_uid,
                                            'manual_time': manual_time
                                        })
                                else:
                                    raise UserError(_("Check-OUT time required greater than Check-IN time `%s`!") % (
                                            exist_check_in + timedelta(hours=6)))

                            else:
                                raise UserError(_("Required Check-IN first on the date!"))
                        else:
                            raise UserError(_("Required Check-OUT time on the date!"))

            return True
