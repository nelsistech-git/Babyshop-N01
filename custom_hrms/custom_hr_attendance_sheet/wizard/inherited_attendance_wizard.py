import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, timedelta, time as dtime
import pytz
import time

_logger = logging.getLogger(__name__)


class AttendanceWizard(models.TransientModel):
    _inherit = 'attendance.wizard'
    _description = 'Inherited Attendance Wizard'

    def cron_process_attendance_policy(self):
        att_obj = self.env["hr.attendance"].sudo()
        current_date = datetime.today()

        hr_att_rows = att_obj.search([('policy_process', '=', '0'), ('attendance_date', '<=', current_date)], order='attendance_date', limit=5000)
        for hr_att in hr_att_rows:
            from_date = hr_att.attendance_date
            to_date = hr_att.attendance_date
            emp = hr_att.employee_id

            is_running_emp = True
            initial_employment_date = emp.initial_employment_date
            if not hr_att.attendance_date:
                hr_att.policy_process = '6'
                continue

            if not initial_employment_date or initial_employment_date > hr_att.attendance_date:
                is_running_emp = False
            else:
                is_separated = emp.is_separated
                if is_separated:
                    separation_date = emp.separation_date
                    if separation_date and separation_date < hr_att.attendance_date:
                        is_running_emp = False

            if emp.active == False or is_running_emp == False:
                hr_att.policy_process = '5'
                hr_att.pl_sign_in = 0
                hr_att.pl_sign_out = 0
                hr_att.late_in = 0
                hr_att.late_in_abs = 0
                hr_att.diff_time = 0
                hr_att.act_late_in = 0
                hr_att.act_diff_time = 0
                hr_att.overtime = 0
                hr_att.act_overtime = 0
                continue

            tz = pytz.timezone(emp.tz)
            if not tz:
                hr_att.policy_process = '2'
                hr_att.pl_sign_in = 0
                hr_att.pl_sign_out = 0
                hr_att.late_in = 0
                hr_att.late_in_abs = 0
                hr_att.diff_time = 0
                hr_att.act_late_in = 0
                hr_att.act_diff_time = 0
                hr_att.overtime = 0
                hr_att.act_overtime = 0                            
                continue
                # raise exceptions.Warning(
                #     "Please add time zone for employee : %s" % emp.name)
            calendar_id = emp.contract_id.resource_calendar_id
            if not calendar_id:
                hr_att.policy_process = '3'
                hr_att.pl_sign_in = 0
                hr_att.pl_sign_out = 0
                hr_att.late_in = 0
                hr_att.late_in_abs = 0
                hr_att.diff_time = 0
                hr_att.act_late_in = 0
                hr_att.act_diff_time = 0
                hr_att.overtime = 0
                hr_att.act_overtime = 0
                continue
                # raise ValidationError(_(
                #     'Please add working hours to the %s `s contract ' % emp.name))
                
            policy_id = hr_att.employee_id.contract_id.att_policy_id
            if not policy_id:
                hr_att.policy_process = '4'
                hr_att.pl_sign_in = 0
                hr_att.pl_sign_out = 0
                hr_att.late_in = 0
                hr_att.late_in_abs = 0
                hr_att.diff_time = 0
                hr_att.act_late_in = 0
                hr_att.act_diff_time = 0
                hr_att.overtime = 0
                hr_att.act_overtime = 0 
                continue
                # raise ValidationError(_(
                #     'Please add Attendance Policy to the %s `s contract ' % emp.name))
            
            
            att_obj.employee_attendance_data_process(emp,from_date,to_date,hr_att)
            
            continue
        
        #------------ Attendance reprocess dates (Back date for previous date entry-leave/public holiday)
        self.attendance_reprocess_dates()

        # ------ OT auto process
        self.env['employee.attendance.sheet.line'].sudo().action_ot_auto_approve()

    def cron_employee_attendance_process(self):
        # today = fields.Datetime.now().date()
        current_datetime = fields.Datetime.now() + timedelta(hours=6)
        today = current_datetime.date()

        att_obj = self.env["hr.attendance"].sudo()

        emp_rows = self.env['hr.employee'].sudo().search([('initial_employment_date', '<=', today)], order='id')
        for emp in emp_rows:
            if emp.is_separated:
                separation_date = emp.separation_date
                if separation_date and separation_date < today:
                    continue
            # ----------
            att_obj.employee_attendance_data_process(emp, today, today, hr_att=None)

    def attendance_reprocess_dates(self):
        att_obj = self.env["hr.attendance"].sudo()

        rows = self.env["attendance.reprocess.dates"].sudo().search([('process_flag', '=', 0)], order='id')
        for rec in rows:
            emp = rec.employee_id
            reprocess_date = rec.date
            if emp and reprocess_date:
                # -----------------
                if not emp.initial_employment_date or emp.initial_employment_date > reprocess_date:
                    continue
                if emp.is_separated:
                    separation_date = emp.separation_date
                    if separation_date and separation_date < reprocess_date:
                        continue
                # ----------------
                att_obj.employee_attendance_data_process(emp, reprocess_date, reprocess_date, hr_att=None)
                rec.process_flag = 1
