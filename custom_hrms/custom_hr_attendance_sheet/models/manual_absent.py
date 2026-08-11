from odoo import models, fields, api, _
from odoo.addons.helper import validator
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, timedelta, time

import logging
_logger = logging.getLogger(__name__)

class ManualAbsent(models.Model):
    _name = 'hr.manual.absent'

    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Manual Absent'
    _order = 'date DESC'
    _rec_name = 'employee_id'
    
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date = fields.Date("Date", required=True)
    day = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], 'Day of Week', required=True)
    reason = fields.Text(string='Reason')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled'),
    ], string="State", default='draft')
    
    user_work_location_id = fields.Many2one('stock.location', related='employee_id.user_work_location_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    id_card_no = fields.Char(string="Employee ID", related='employee_id.id_card_no')
    device_user_id = fields.Char(string='Biometric Device ID', related='employee_id.device_user_id')
    
    #------------
    is_apply = fields.Boolean(string='Apply?', default=False)
    apply_date = fields.Datetime("Apply Date")
    apply_uid = fields.Many2one("res.users", string="Apply User")
    
    is_reverse = fields.Boolean(string='Reverse?', default=False)
    reverse_date = fields.Datetime("Reverse Date")
    reverse_uid = fields.Many2one("res.users", string="Apply User")
    
    #
    @api.onchange('date')
    def _onchange_date(self):
        if self.date:
            day_str = str(self.date.weekday())   
            self.day = day_str
            
    def unlink(self):
        for record in self:
            if record.state !='draft':
                raise UserError(_('Only Draft record can be deleted!'))
        return super(ManualAbsent, self).unlink()
    
    def action_draft(self):
        self.state = 'draft'

    def action_confirm(self):
        self.state = 'confirm'

    def action_approve(self):
        self.state = 'approve'

    def action_cancel(self):
        self.state = 'cancel'

    @api.constrains('date')
    def _check_unique_constraint_employee_date(self):
        
        if self.date:
            current_datetime = fields.Datetime.now() + timedelta(hours=6)
            today = current_datetime.date()
            if self.date > today:
                raise UserError(_('Absent date can not be future date!'))
            # else:
            #     msg = 'Employee same date "%s"' % self.employee_id.name
            #     envobj = self.env['hr.manual.absent']
            #     conditionlist = [('employee_id', '=', self.employee_id.id),('date', '=', self.date)]
            #     validator.check_duplicate_value(self, envobj, conditionlist, msg)
            
    
    def action_is_apply(self):
        current_datetime = fields.Datetime.now() #+ timedelta(hours=6)
        #today = current_datetime.date()
        self.is_apply = True
        self.apply_date = current_datetime
        self.apply_uid = self.env.uid
        
        check_in = datetime.combine(self.date, time(0,0,0))
        check_out = datetime.combine(self.date, time(0,1,0))
        
        pl_sign_in = self.employee_id.resource_calendar_id.hour_from_per_day_m
        pl_sign_out = self.employee_id.resource_calendar_id.hour_to_per_day_e
        act_diff_time =  self.employee_id.resource_calendar_id.hours_per_day
        
        att_obj = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id), ('attendance_date', '=', self.date)], limit=1)
        if att_obj:
            att_obj.note = self.reason
            
            att_obj.policy_process = '1'
            att_obj.manual_absent = True   
            att_obj.status = 'ab'         
            #att_obj.pl_sign_in = 0
            #att_obj.pl_sign_out = 0
            # att_obj.act_diff_time = 0
            
            #att_obj.late_in = 0
            #att_obj.diff_time = 0
            #att_obj.act_late_in = 0
            #att_obj.overtime = 0
            #att_obj.act_overtime = 0
        else:
            #raise UserError("No attendance found for '%s'" % self.employee_id.name)
            #synch_ignore_constraints = self.env.context.get('synch_ignore_constraints', False)
            HrAttendance = self.env['hr.attendance'].with_context(synch_ignore_constraints=False)
            
            vals = {
                    'employee_id': self.employee_id.id,
                    'user_work_location_id': self.user_work_location_id.id if self.user_work_location_id else None,
                    'attendance_date': self.date,
                    'check_in': check_in,
                    #'checkin_device_id': uatt.device_id.id,
                    'check_out': check_out,
                    #'manual_flag': 0,
                    'punch_count': 0,
                    'manual_absent': True,
                    'policy_process': '1',
                    'status': 'ab',
                    'pl_sign_in': pl_sign_in,
                    'pl_sign_out': pl_sign_out,
                    'act_diff_time': act_diff_time
                    }
            try:
                HrAttendance.create(vals)
            except Exception as e:
                _logger.error(e)
                
        #------------------ 
        att_line = self.env["employee.attendance.sheet.line"].sudo()        
        att_line_obj = att_line.search([('employee_id.id', '=', self.employee_id.id), ('date', '=', self.date)], limit=1)   
        day_str = str(self.date.weekday())
        
        if att_line_obj:
            write_vals = {
                'pl_sign_in': att_line_obj[0].pl_sign_in or pl_sign_in,
                'pl_sign_out': att_line_obj[0].pl_sign_out or pl_sign_out,
                # 'act_diff_time': att_line_obj[0].act_diff_time or act_diff_time,
                # 'diff_time': att_line_obj[0].act_diff_time or act_diff_time,


                'act_diff_time': 0,
                'diff_time': 0,
                'worked_hours': 0,
                'ac_sign_in': 0,
                'ac_sign_out': 0,
                'late_in': 0,
                'late_in_abs': 0,
                'act_late_in': 0,
                'overtime': 0,
                'act_overtime': 0,
                'status': 'ab',
                'note': self.reason,
                'manual_absent': True
            }
            att_line_obj.write(write_vals)
        else:
            values = {
                'employee_id': self.employee_id.id,
                'date': self.date,
                'day': day_str,
                'status': 'ab',
                'note': self.reason,
                'pl_sign_in': pl_sign_in,
                'pl_sign_out': pl_sign_out,
                'act_diff_time': act_diff_time,
                'diff_time': act_diff_time,
                'manual_absent': True
            }
            att_line.create(values)
    
    def action_is_reverse(self):
        current_datetime = fields.Datetime.now() #+ timedelta(hours=6)
        
        self.is_reverse = True
        self.reverse_date = current_datetime
        self.reverse_uid = self.env.uid
        
        att_obj = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id), ('attendance_date', '=', self.date)], limit=1)
        if att_obj:
            att_obj.active = False
            
        #------------------ 
        att_obj2 = self.env["hr.attendance"].sudo()
        att_line = self.env["employee.attendance.sheet.line"].sudo()        
        att_line_obj = att_line.search([('employee_id.id', '=', self.employee_id.id), ('date', '=', self.date)], limit=1)   
        if att_line_obj:
            att_line_obj.unlink()
            att_obj2.employee_attendance_data_process(self.employee_id,self.date,self.date, hr_att = None)
            

        att_rows = self.env['user.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                       ('valid', '=', True),
                                                        ('timestamp', '>=', datetime.combine(self.date, time(0,0,0))),
                                                        ('timestamp', '<=', datetime.combine(self.date, time(23,59,59)))        
                                                    ])
        for row in att_rows:
            row.process_flag = 0
        
            