import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, timedelta, time as dtime
import pytz
import time

_logger = logging.getLogger(__name__)


class AttendanceWizard(models.TransientModel):
    _name = 'attendance.wizard'
    _description = 'Attendance Wizard'

    @api.model
    def _get_all_device_ids(self):
        all_devices = self.env['attendance.device'].search([('state', '=', 'confirmed')])
        if all_devices:
            return all_devices.ids
        else:
            return []

    device_ids = fields.Many2many('attendance.device', string='Devices', default=_get_all_device_ids, domain=[('state', '=', 'confirmed')])
    fix_attendance_valid_before_synch = fields.Boolean(string='Fix Attendance Valid', help="If checked, Odoo will recompute all attendance data for their valid"
                                                     " before synchronizing with HR Attendance (upon you hit the 'Synchronize Attendance' button)")
    #not used
    def download_attendance_manually(self):
        # TODO: remove me after 12.0
        self.action_download_attendance()

    # manual from base wizard
    def action_download_attendance(self):
        if not self.device_ids:
            raise UserError(_('You must select at least one device to continue!'))
        self.device_ids.action_attendance_download()

    def cron_download_device_attendance(self):
        devices = self.env['attendance.device'].sudo().search([('state', '=', 'confirmed')])
        #devices.action_attendance_download()

        for device in devices:
            try:
                device.action_attendance_download()
            except:
                continue

            self.env.cr.commit()
            time.sleep(2)

        #-------- sync after downlaod
        self.cron_sync_attendance()


    def cron_sync_attendance(self):
        self.with_context(synch_ignore_constraints=True).sync_attendance_ord_shift()

        # is_rostering_attendance_process = self.env['custom.common.settings'].search(
        #     [('key', '=', 'is_rostering_attendance_process')], limit=1)
        # if is_rostering_attendance_process.value:
        #     self.with_context(synch_ignore_constraints=True).sync_attendance_ord_shift()
        # else:
        #     self.with_context(synch_ignore_constraints=True).sync_attendance()

    def sync_attendance(self):
        """
        This method will synchronize all downloaded attendance data with Odoo attendance data.
        It do not download attendance data from the devices.
        """
        if self.fix_attendance_valid_before_synch:
            self.action_fix_user_attendance_valid()

        synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)

        error_msg = {}
        HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=synch_ignore_constraints)

        unsync_data = self.env['user.attendance'].sudo().search([
            ('valid', '=', True),
            ('employee_id', '!=', False),
            ('process_flag', '=', 0)], order='timestamp ASC', limit=5000)

        for uatt in unsync_data:
            employee = uatt.user_id.employee_id
            uatt_timestamp = uatt.timestamp

            att_date = uatt_timestamp.date()
            attendance_type = uatt.attendance_type

            calendar_id = employee.contract_id.resource_calendar_id or False
            is_over_ride_day = False
            if calendar_id:
                is_over_ride_day = calendar_id.is_over_ride_day

            manual_flag = 0
            if attendance_type == '20':
                manual_flag = 1

            # att_dt = attendance_date.strftime('%Y-%m-%d %H:%M:%S')
            # start_time = datetime.datetime.strptime(att_dt, '%Y-%m-%d %H:%M:%S') + timedelta(hours=from_hour_s) - timedelta(hours=6)
            hr_attendance = HrAttendance.sudo().search([('employee_id', '=', employee.id), ('attendance_date', '=', att_date)],
                                                limit=1)
            if hr_attendance:
                try:
                    check_in = hr_attendance[0].check_in
                    check_out = hr_attendance[0].check_out
                    manual_flag_exist = hr_attendance[0].manual_flag
                    punch_count = hr_attendance[0].punch_count

                    if manual_flag_exist == 1:
                        manual_flag = 1

                    if uatt_timestamp > check_in:
                        if check_out == None or check_out == '' or uatt_timestamp > check_out:
                            hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).sudo().write({
                                'check_out': uatt_timestamp,
                                'checkout_device_id': uatt.device_id.id,
                                'manual_flag': manual_flag,
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
                                'act_overtime': 0
                            })

                    else:
                        hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).sudo().write({
                            'check_in': uatt_timestamp,
                            'checkin_device_id': uatt.device_id.id,
                            'manual_flag': manual_flag,
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
                            'act_overtime': 0
                        })

                except ValidationError as e:
                    if uatt.device_id not in error_msg:
                        error_msg[uatt.device_id] = ""

                    msg = ""
                    att_check_time = fields.Datetime.context_timestamp(uatt, uatt_timestamp)
                    msg += str(e) + "<br />"
                    msg += _("'Check Out' time cannot be earlier than 'Check In' time. Debug information:<br />"
                             "* Employee: <strong>%s</strong><br />"
                             "* Type: %s<br />"
                             "* Attendance Check Time: %s<br />") % (
                           employee.name, uatt.type, fields.Datetime.to_string(att_check_time))
                    _logger.error(msg)
                    error_msg[uatt.device_id] += msg

            else:
                # create hr attendance data
                uatt_timestamp_out = uatt_timestamp + timedelta(minutes=1)
                user_work_location_id = ''
                if uatt.user_work_location_id:
                    user_work_location_id = uatt.user_work_location_id.id

                vals = {
                    'employee_id': employee.id,
                    'user_work_location_id': user_work_location_id,
                    'attendance_date': att_date,
                    'check_in': uatt_timestamp,
                    'checkin_device_id': uatt.device_id.id,
                    'check_out': uatt_timestamp_out,
                    'manual_flag': manual_flag,
                    'punch_count': 1,
                    'resource_calendar_id': calendar_id.id,
                    'is_over_ride_day': is_over_ride_day,
                    # 'activity_id': attendance_activity.id,
                }
                hr_attendance = HrAttendance.sudo().create(vals)

            if hr_attendance:
                uatt.write({
                    'hr_attendance_id': hr_attendance.id,
                    'process_flag': 1
                })

        if bool(error_msg):
            for device in error_msg.keys():
                if not device.debug_message:
                    continue
                device.message_post(body=error_msg[device])

    def sync_attendance_ord_shift(self):
        """
        This method will synchronize all downloaded attendance data with Odoo attendance data.
        It do not download attendance data from the devices.
        """
        if self.fix_attendance_valid_before_synch:
            self.action_fix_user_attendance_valid()

        synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)

        error_msg = {}
        HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=synch_ignore_constraints)
        HrAttendance_obj = self.env['hr.attendance']

        unsync_data = self.env['user.attendance'].search([
            ('valid', '=', True),
            ('employee_id', '!=', False),
            ('process_flag', '=', 0)], order='timestamp ASC', limit=5000)
        
        for uatt in unsync_data:
            employee = uatt.user_id.employee_id
            uatt_timestamp = uatt.timestamp
            uatt_timestamp_tz = uatt_timestamp + timedelta(hours=6)

            att_date = uatt_timestamp_tz.date()
            attendance_type = uatt.attendance_type
            
            manual_flag = 0
            if attendance_type == '20':
                manual_flag = 1


            #-------------- over-ride-day (ORD) shift
            data_list = HrAttendance_obj.get_emp_shifting_schedule_data(employee, att_date, uatt_timestamp_tz)
            if len(data_list)==5:
                att_date = data_list[0]
                calendar_id = data_list[1]
                is_over_ride_day = data_list[2]
                calendar_id_prev = data_list[3]
                is_over_ride_day_prev = data_list[4]
            else:
                continue

            if not calendar_id:
                continue

            #-------------
            hr_attendance = HrAttendance.search([('employee_id', '=', employee.id), ('attendance_date', '=', att_date)], limit=1)
            if hr_attendance:
                try:
                    check_in = hr_attendance[0].check_in
                    check_out = hr_attendance[0].check_out
                    manual_flag_exist = hr_attendance[0].manual_flag
                    punch_count = hr_attendance[0].punch_count
                    
                    if manual_flag_exist == 1:
                        manual_flag = 1
                        
                    if uatt_timestamp > check_in:
                        if check_out == None or check_out == '' or uatt_timestamp > check_out:
                            hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                                'check_out': uatt_timestamp,
                                'checkout_device_id': uatt.device_id.id,
                                'manual_flag': manual_flag,
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
                                'act_overtime': 0
                                })
                    else:
                        hr_attendance.with_context(synch_ignore_constraints=synch_ignore_constraints).write({
                            'check_in': uatt_timestamp,
                            'checkin_device_id': uatt.device_id.id,
                            'manual_flag': manual_flag,
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
                            'act_overtime': 0
                            })
                    
                except ValidationError as e:
                    if uatt.device_id not in error_msg:
                        error_msg[uatt.device_id] = ""

                    msg = ""
                    att_check_time = fields.Datetime.context_timestamp(uatt, uatt_timestamp)
                    msg += str(e) + "<br />"
                    msg += _("'Check Out' time cannot be earlier than 'Check In' time. Debug information:<br />"
                                  "* Employee: <strong>%s</strong><br />"
                                  "* Type: %s<br />"
                                  "* Attendance Check Time: %s<br />") % (employee.name, uatt.type, fields.Datetime.to_string(att_check_time))
                    _logger.error(msg)
                    error_msg[uatt.device_id] += msg
                
            else:
                # create hr attendance data
                uatt_timestamp_out = uatt_timestamp  + timedelta(minutes=1)
                user_work_location_id = ''
                if uatt.user_work_location_id:
                    user_work_location_id = uatt.user_work_location_id.id

                vals = {
                    'employee_id': employee.id,
                    'user_work_location_id':user_work_location_id,
                    'attendance_date': att_date,
                    'check_in': uatt_timestamp,
                    'checkin_device_id': uatt.device_id.id,
                    'check_out': uatt_timestamp_out,
                    'manual_flag': manual_flag,
                    'punch_count': 1,
                    'resource_calendar_id': calendar_id.id,
                    'is_over_ride_day': is_over_ride_day,
                    'resource_calendar_id_prev': calendar_id_prev.id,
                    'is_over_ride_day_prev': is_over_ride_day_prev
                    #'activity_id': attendance_activity.id,
                    }
                hr_attendance = HrAttendance.create(vals)

            if hr_attendance:
                uatt.write({
                    'hr_attendance_id': hr_attendance.id,
                    'process_flag':1
                    })

        if bool(error_msg):
            for device in error_msg.keys():
                if not device.debug_message:
                    continue
                device.message_post(body=error_msg[device])

    def clear_attendance(self):
        if not self.device_ids:
            raise UserError(_('You must select at least one device to continue!'))
        if not self.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            raise UserError(_('Only HR Attendance Managers can manually clear device attendance data'))

        for device in self.device_ids:
            device.clearAttendance()

    def action_fix_user_attendance_valid(self):
        self.env['user.attendance'].sudo().search([])._update_valid()

    #transfer func to att sheet
    # def cron_process_attendance_policy(self):
    #     att_obj = self.env["hr.attendance"].sudo()
    #     hr_att_rows = att_obj.search([('policy_process', '=', '0')], order='attendance_date', limit=5000)
    #     for hr_att in hr_att_rows:
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
    #
    #         att_obj.employee_attendance_data_process(emp,from_date,to_date,hr_att)
    #
    #         continue
    #
    #     #------------ Attendance reprocess dates (Back date for previous date entry-leave/public holiday)
    #     self.attendance_reprocess_dates()
    #
    #     # ------ OT auto process
    #     self.env['employee.attendance.sheet.line'].sudo().action_ot_auto_approve()
    #
    # def cron_employee_attendance_process(self):
    #     #today = fields.Datetime.now().date()
    #     current_datetime = fields.Datetime.now() + timedelta(hours=6)
    #     today = current_datetime.date()
    #
    #     att_obj = self.env["hr.attendance"].sudo()
    #
    #     emp_rows = self.env['hr.employee'].sudo().search([('initial_employment_date', '<=', today)], order='id')
    #     for emp in emp_rows:
    #         if emp.is_separated:
    #             separation_date = emp.separation_date
    #             if separation_date and separation_date < today:
    #                 continue
    #         #----------
    #         att_obj.employee_attendance_data_process(emp,today,today, hr_att = None)
    #
    # def attendance_reprocess_dates(self):
    #     att_obj = self.env["hr.attendance"].sudo()
    #
    #     rows = self.env["attendance.reprocess.dates"].sudo().search([('process_flag', '=', 0)], order='id')
    #     for rec in rows:
    #         emp = rec.employee_id
    #         reprocess_date = rec.date
    #         if emp and reprocess_date:
    #             #-----------------
    #             if not emp.initial_employment_date or emp.initial_employment_date > reprocess_date:
    #                 continue
    #             if emp.is_separated:
    #                 separation_date = emp.separation_date
    #                 if separation_date and separation_date < reprocess_date:
    #                     continue
    #             #----------------
    #             att_obj.employee_attendance_data_process(emp,reprocess_date,reprocess_date, hr_att = None)
    #             rec.process_flag = 1
            
            
