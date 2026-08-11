from odoo import models, fields, api, _
from odoo.addons.helper import validator
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, timedelta, time

import logging
_logger = logging.getLogger(__name__)

class ManualWeekendAlter(models.Model):
    _name = 'hr.manual.weekend.alter'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Manual Weekend Alter'
    _order = 'date_from DESC'
    _rec_name = 'employee_id'
    
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    
    date_from = fields.Date("From Date (Weekend)", required=True)
    day_from = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], 'From Day', required=True)
    
    date_to = fields.Date("To Date", required=True)
    day_to = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], 'To Day', required=True)
    
    reason = fields.Text(string='Reason')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled'),
    ], string="State", default='draft')
    
    user_work_location_id = fields.Many2one('stock.location')
    department_id = fields.Many2one('hr.department')
    id_card_no = fields.Char(string="Employee ID")
    device_user_id = fields.Char(string='Biometric Device ID')
    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Schedule', help="Employee's working schedule.")
    
    #------------
    is_apply = fields.Boolean(string='Apply?', default=False)
    apply_date = fields.Datetime("Apply Date")
    apply_uid = fields.Many2one("res.users", string="Apply User")
    
    is_reverse = fields.Boolean(string='Reverse?', default=False)
    reverse_date = fields.Datetime("Reverse Date")
    reverse_uid = fields.Many2one("res.users", string="Apply User")
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.user_work_location_id = self.employee_id.user_work_location_id.id if self.employee_id.user_work_location_id else None
            self.department_id = self.employee_id.department_id.id if self.employee_id.department_id else None
            self.id_card_no = self.employee_id.id_card_no
            self.device_user_id = self.employee_id.device_user_id
            self.resource_calendar_id = self.employee_id.resource_calendar_id.id if self.employee_id.resource_calendar_id else None
    
    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from:
            day_str = str(self.date_from.weekday())   
            self.day_from = day_str
    
    @api.onchange('date_to')
    def _onchange_date_to(self):
        if self.date_to:
            day_str = str(self.date_to.weekday())   
            self.day_to = day_str
            
    def unlink(self):
        for record in self:
            if record.state !='draft':
                raise UserError(_('Only Draft record can be deleted!'))
        return super(ManualWeekendAlter, self).unlink()
        
    def action_draft(self):
        self.state = 'draft'
        
    def action_confirm(self):
        date_from = self.date_from
        date_to = self.date_to
        
        att_line = self.env["employee.attendance.sheet.line"].sudo()
        att_line_obj1 = att_line.search([('employee_id', '=', self.employee_id.id), ('date', '=', date_from), ('status', '=', 'weekend')], limit=1)
        if not att_line_obj1:
            raise UserError(_('From Date required weekend in Employee Attendance Details!'))
        else:
            att_line_obj2 = att_line.search([('employee_id.id', '=', self.employee_id.id), ('date', '=', date_to), ('status', '=', 'ab')], limit=1)
            if not att_line_obj2:
                raise UserError(_('To Date required absent day in Employee Attendance Details!'))
            else:
                pass
        self.state = 'confirm'
        
    def action_approve(self):
        date_from = self.date_from
        date_to = self.date_to
        
        att_line = self.env["employee.attendance.sheet.line"].sudo()
        att_line_obj1 = att_line.search([('employee_id.id', '=', self.employee_id.id), ('date', '=', date_from), ('status', '=', 'weekend')], limit=1)
        if not att_line_obj1:
            raise UserError(_('From Date required weekend in Employee Attendance Details!'))
        else:
            att_line_obj2 = att_line.search([('employee_id.id', '=', self.employee_id.id), ('date', '=', date_to), ('status', '=', 'ab')], limit=1)
            if not att_line_obj2:
                raise UserError(_('To Date required absent day in Employee Attendance Details!'))
            else:
                pass
        self.state = 'approve'
    def action_cancel(self):
        self.state = 'cancel'

    @api.constrains('date_from','date_to')
    def _check_unique_constraint_date(self):
        current_datetime = fields.Datetime.now() + timedelta(hours=6)
        today = current_datetime.date()
        
        if self.date_from:            
            if self.date_from > today:
                raise UserError(_('From Date can not be future date!'))
        
        if self.date_to:
            if self.date_to > today:
                raise UserError(_('To Date can not be future date!'))
            
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
        
        date_from = self.date_from
        date_to = self.date_to
        
        #pl_sign_in = self.employee_id.resource_calendar_id.hour_from_per_day_m
        #pl_sign_out = self.employee_id.resource_calendar_id.hour_to_per_day_e
        #act_diff_time =  self.employee_id.resource_calendar_id.hours_per_day
        
        #------------------ 
        att_line = self.env["employee.attendance.sheet.line"].sudo()
        att_line_obj1 = att_line.search([('employee_id.id', '=', self.employee_id.id), ('date', '=', date_from), ('status', '=', 'weekend')], limit=1)
        if not att_line_obj1:
            raise UserError(_('From Date required weekend in Employee Attendance Details!'))
        else:
            att_line_obj2 = att_line.search([('employee_id.id', '=', self.employee_id.id), ('date', '=', date_to), ('status', '=', 'ab')], limit=1)
            if not att_line_obj2:
                raise UserError(_('To Date required absent day in Employee Attendance Details!'))
            else:
                var1 = {
                    'status': '',
                    'manual_weekend':True,
                    'overtime': 0,
                    'act_overtime': 0
                    }
                var2 = {
                    'status': 'weekend',
                    'manual_weekend':True
                    }                
                att_line_obj1.write(var1)
                att_line_obj2.write(var2)
                
                         
                att_obj1 = self.env['hr.attendance'].sudo().search([('employee_id', '=', self.employee_id.id), ('attendance_date', '=', date_from)], limit=1)
                if att_obj1:
                    att_obj1.write({'manual_weekend':True,'status': ''})
                    
                att_obj2 = self.env['hr.attendance'].sudo().search([('employee_id', '=', self.employee_id.id), ('attendance_date', '=', date_to)], limit=1)
                if att_obj2:
                    att_obj2.write({'manual_weekend':True,'status': 'weekend'})
                    
                    
    def action_is_reverse(self):
        current_datetime = fields.Datetime.now() #+ timedelta(hours=6)
        
        self.is_reverse = True
        self.reverse_date = current_datetime
        self.reverse_uid = self.env.uid
        
        date_from = self.date_from
        date_to = self.date_to
        
        #------------------ 
        att_obj = self.env["hr.attendance"].sudo()
        att_obj1 = att_obj.search([('employee_id', '=', self.employee_id.id), ('attendance_date', '=', date_from)], limit=1)
        if att_obj1:
            att_obj1.active = False        
        att_obj2 = att_obj.search([('employee_id', '=', self.employee_id.id), ('attendance_date', '=', date_to)], limit=1)
        if att_obj2:
            att_obj2.active = False            
        #------------------ 
        
        att_line = self.env["employee.attendance.sheet.line"].sudo()        
        att_line_obj1 = att_line.search([('employee_id.id', '=', self.employee_id.id), ('date', '=', date_from)], limit=1)   
        if att_line_obj1:
            att_line_obj1.unlink()            
            att_obj.employee_attendance_data_process(self.employee_id,date_from,date_from, hr_att = None)
        
        att_line_obj2 = att_line.search([('employee_id.id', '=', self.employee_id.id), ('date', '=', date_to)], limit=1)   
        if att_line_obj2:
            att_line_obj2.unlink()            
            att_obj.employee_attendance_data_process(self.employee_id,date_to,date_to, hr_att = None)        
        #---------------------
        att_rows1 = self.env['user.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                       ('valid', '=', True),
                                                        ('timestamp', '>=', datetime.combine(date_from, time(0,0,0))),
                                                        ('timestamp', '<=', datetime.combine(date_from, time(23,59,59)))        
                                                    ])
        for row1 in att_rows1:
            row1.process_flag = 0
        
        att_rows2 = self.env['user.attendance'].search([('employee_id', '=', self.employee_id.id),
                                                       ('valid', '=', True),
                                                        ('timestamp', '>=', datetime.combine(date_to, time(0,0,0))),
                                                        ('timestamp', '<=', datetime.combine(date_to, time(23,59,59)))        
                                                    ])
        for row2 in att_rows2:
            row2.process_flag = 0
            
        
            