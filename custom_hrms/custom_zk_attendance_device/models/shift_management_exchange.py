from odoo import models, fields, api
import datetime
from datetime import datetime
from odoo.addons.helper import validator
from odoo.exceptions import UserError, ValidationError


class ShiftManagementExchange(models.Model):
    _name = "shift.management.exchange"
    _description = 'Shift Exchange/Alter'
    _rec_name = 'date'
    _order = 'date desc'

    def _default_employee(self):
        return self.env['hr.employee'].search([('is_rostering_employee', '=', True), ('user_id', '=', self.env.uid)], limit=1)

    @api.model
    def _set_domain_employee(self):
        if self.user_has_groups('custom_zk_attendance_device.group_emp_shifting_administrator'):
            return [('is_rostering_employee', '=', True)]
        elif self.user_has_groups('custom_zk_attendance_device.group_emp_shifting_user'):
            return [('is_rostering_employee', '=', True),'|',('user_id', '=', self.env.uid), ('parent_id.user_id', '=', self.env.uid)]
        else:
            return [('is_rostering_employee', '=', True), ('user_id', '=', self.env.uid)]

    type = fields.Selection([
        ('exchange', 'Exchange'),
        ('alter', 'Alter'),
    ], string='Type', readonly=True, copy=False, index=True, default='exchange', required=True)

    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    remarks = fields.Text(string='Remarks')

    from_employee_id = fields.Many2one('hr.employee', string='1st Employee', required=True, default=_default_employee, domain=lambda self: self._set_domain_employee())
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    department_id = fields.Many2one('hr.department', string='Department')
    job_id = fields.Many2one('hr.job', string="Designation")
    manager_id = fields.Many2one('hr.employee', string='Reporting Manager')


    from_resource_calendar_id = fields.Many2one('resource.calendar', string='1st Working Hours/Shift',
                                           help="Employee's working schedule.")
    from_hour_from_per_day_m = fields.Float(string='Start Time', related="from_resource_calendar_id.hour_from_per_day_m")
    from_hour_to_per_day_e = fields.Float(string='End Time', related="from_resource_calendar_id.hour_to_per_day_e")
    from_is_over_ride_day = fields.Boolean(string="Over-Ride Day/Night Shift",
                                      related="from_resource_calendar_id.is_over_ride_day")

    #----------
    to_employee_id = fields.Many2one('hr.employee', string='2nd Employee',
                                  domain=[('is_rostering_employee', '=', True)])
    to_user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    to_department_id = fields.Many2one('hr.department', string='Department')
    to_job_id = fields.Many2one('hr.job', string="Designation")
    to_manager_id = fields.Many2one('hr.employee', string='Reporting Manager')

    to_resource_calendar_id = fields.Many2one('resource.calendar', string='2nd Working Hours/Shift',
                                                help="Employee's working schedule.")
    to_hour_from_per_day_m = fields.Float(string='Start Time', related="to_resource_calendar_id.hour_from_per_day_m")
    to_hour_to_per_day_e = fields.Float(string='End Time', related="to_resource_calendar_id.hour_to_per_day_e")
    to_is_over_ride_day = fields.Boolean(string="Over-Ride Day/Night Shift",
                                           related="to_resource_calendar_id.is_over_ride_day")

    request_date = fields.Datetime(string='Requested Date')
    accept_date = fields.Datetime(string='Accepted Date')
    approve_date = fields.Datetime(string='Approved Date')

    requested_by_id = fields.Many2one('hr.employee', string='Requested By')
    accepted_by_id = fields.Many2one('hr.employee', string='Accepted By')
    approved_by_id = fields.Many2one('hr.employee', string='Approved By')

    line_ids = fields.One2many('shift.management.exchange.shift', 'head_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Requested'),
        ('accept', 'Accepted'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, default='draft')

    is_accept_user = fields.Boolean('Is Accept User?', compute='_compute_is_accept_user')

    @api.onchange('from_employee_id', 'date')
    def _onchange_from_employee_id(self):
        if self.date and self.from_employee_id:
            shift_req_obj = self.env['shift.management.request'].sudo().search([('employee_id', '=', self.from_employee_id.id), ('date_from', '<=', self.date), ('date_to', '>=', self.date), ('state', '=', 'approve')], limit=1)
            if not shift_req_obj:
                self.from_resource_calendar_id = None
                if self.type=='exchange':
                    raise ValidationError('From Employee `%s` has no Approved Shift Request/Plan On the Date!' %(self.from_employee_id.name))
                else:
                    raise ValidationError('Employee `%s` has no Approved Shift Request/Plan On the Date!' % (
                        self.from_employee_id.name))
            else:
                self.from_resource_calendar_id = shift_req_obj.resource_calendar_id.id or False

                if self.from_employee_id:
                    self.user_work_location_id = self.from_employee_id.user_work_location_id.id or False

                    self.job_id = self.from_employee_id and self.from_employee_id.job_id and \
                                  self.from_employee_id.job_id.id or False
                    self.department_id = self.from_employee_id and self.from_employee_id.department_id and \
                                         self.from_employee_id.department_id.id or False
                    self.manager_id = self.department_id and self.department_id.manager_id and \
                                      self.department_id.manager_id.id or self.from_employee_id.parent_id.id or False


    @api.onchange('to_employee_id', 'date')
    def _onchange_from_to_employee_id(self):
        if self.date and self.to_employee_id:
            shift_req_obj = self.env['shift.management.request'].sudo().search([('employee_id', '=', self.to_employee_id.id), ('date_from', '<=', self.date), ('date_to', '>=', self.date), ('state', '=', 'approve')], limit=1)
            if not shift_req_obj:
                self.to_resource_calendar_id= None
                raise ValidationError('To Employee `%s` has no Approved Shift Request On the date!' %(self.to_employee_id.name))
            else:
                self.to_resource_calendar_id = shift_req_obj.resource_calendar_id.id or False
                if self.to_employee_id:
                    self.to_user_work_location_id = self.to_employee_id.user_work_location_id.id or False

                    self.to_job_id = self.to_employee_id and self.to_employee_id.job_id and \
                                  self.to_employee_id.job_id.id or False
                    self.to_department_id = self.to_employee_id and self.to_employee_id.department_id and \
                                         self.to_employee_id.department_id.id or False
                    self.to_manager_id = self.to_department_id and self.to_department_id.manager_id and \
                                      self.to_department_id.manager_id.id or self.to_employee_id.parent_id.id or False

    #@api.depends('to_employee_id')
    def _compute_is_accept_user(self):
        for rec in self:
            if rec.type == 'exchange':
                if rec.to_employee_id:
                    if self.user_has_groups('custom_zk_attendance_device.group_emp_shifting_administrator'):
                        rec.is_accept_user = True
                    else:
                        if self.user_has_groups('custom_zk_attendance_device.group_emp_shifting_user'):
                            if rec.to_employee_id.user_id.id == self.env.uid or rec.to_manager_id.user_id.id == self.env.uid:
                                rec.is_accept_user = True
                            else:
                                rec.is_accept_user = False
                        else:
                            rec.is_accept_user = False
                else:
                    rec.is_accept_user = False
            else:
                rec.is_accept_user = False

    @api.constrains('from_employee_id', 'to_employee_id', 'date')
    def _check_unique_date_employee_id(self):
        for rec in self:
            msg = 'Same request of the date "%s"' % (rec.date)
            envobj = self.env['shift.management.exchange']
            conditionlist = [('date', '=', rec.date), ('from_employee_id', '=', rec.from_employee_id.id),
                             ('to_employee_id', '=', rec.to_employee_id.id)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    def action_draft(self):
        line_objs = self.env['shift.management.exchange.shift'].sudo().search([('head_id', '=', self.id)])
        for rec in line_objs:
            rec.unlink()

        self.state = 'draft'

    def action_confirm(self):
        current_datetime = fields.Datetime.now()
        for rec in self:
            if rec.type=='exchange':
                if rec.from_employee_id == rec.to_employee_id:
                    raise ValidationError('From and To Employee can not be same!')
                elif rec.from_resource_calendar_id == rec.to_resource_calendar_id:
                    raise ValidationError('From and To Shift can not be same!')
            elif rec.type=='alter':
                if rec.from_resource_calendar_id == rec.to_resource_calendar_id:
                    raise ValidationError('Previous and New Shift can not be same!')

            #--------------
            rec.state = 'confirm'
            rec.request_date = current_datetime
            employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            rec.requested_by_id = employee_id and employee_id.id or False

    def action_accept(self):
        current_datetime = fields.Datetime.now()
        for rec in self:
            #--------------
            rec.state = 'accept'
            rec.accept_date = current_datetime
            employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            rec.accepted_by_id = employee_id and employee_id.id or False

    def action_approve(self):
        #--------------
        current_datetime = fields.Datetime.now()
        line_obj = self.env['shift.management.exchange.shift'].sudo()

        line_objs = line_obj.search([('head_id', '=', self.id)])
        for rec1 in line_objs:
            rec1.unlink()

        #-----------
        for rec in self:
            if rec.type == 'exchange':
                if rec.from_employee_id == rec.to_employee_id:
                    raise ValidationError('From and To Employee can not be same!')
                elif rec.from_resource_calendar_id == rec.to_resource_calendar_id:
                    raise ValidationError('From and To Shift can not be same!')

                #-------
                line_obj.create({
                    'head_id': rec.id,
                    'employee_id': rec.from_employee_id.id,
                    'user_work_location_id': rec.from_employee_id.user_work_location_id.id or False,
                    'job_id': rec.from_employee_id.job_id and rec.from_employee_id.job_id.id or False,
                    'department_id': rec.from_employee_id.department_id and rec.from_employee_id.department_id.id or False,
                    'manager_id': rec.from_employee_id.department_id and rec.from_employee_id.department_id.manager_id and rec.from_employee_id.department_id.manager_id.id or rec.from_employee_id.parent_id.id or False,
                    'date': rec.date,
                    'resource_calendar_id': rec.to_resource_calendar_id.id,
                    'type': 'exchange',
                    'state': 'approve'
                })
                line_obj.create({
                    'head_id': rec.id,
                    'employee_id': rec.to_employee_id.id,
                    'user_work_location_id': rec.to_employee_id.user_work_location_id.id or False,
                    'job_id': rec.to_employee_id.job_id and rec.to_employee_id.job_id.id or False,
                    'department_id': rec.to_employee_id.department_id and rec.to_employee_id.department_id.id or False,
                    'manager_id': rec.to_employee_id.department_id and rec.to_employee_id.department_id.manager_id and rec.to_employee_id.department_id.manager_id.id or rec.to_employee_id.parent_id.id or False,
                    'date': rec.date,
                    'resource_calendar_id': rec.from_resource_calendar_id.id,
                    'state': 'approve'
                })
            elif rec.type == 'alter':
                if rec.from_resource_calendar_id == rec.to_resource_calendar_id:
                    raise ValidationError('Previous and New Shift can not be same!')

                line_obj.create({
                    'head_id': rec.id,
                    'employee_id': rec.from_employee_id.id,
                    'user_work_location_id': rec.from_employee_id.user_work_location_id.id or False,
                    'job_id': rec.from_employee_id.job_id and rec.from_employee_id.job_id.id or False,
                    'department_id': rec.from_employee_id.department_id and rec.from_employee_id.department_id.id or False,
                    'manager_id': rec.from_employee_id.department_id and rec.from_employee_id.department_id.manager_id and rec.from_employee_id.department_id.manager_id.id or rec.from_employee_id.parent_id.id or False,
                    'date': rec.date,
                    'resource_calendar_id': rec.to_resource_calendar_id.id,
                    'type': 'alter',
                    'state': 'approve'
                })

            rec.state = 'approve'
            rec.approve_date = current_datetime

            employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            rec.approved_by_id = employee_id and employee_id.id or False

    def action_cancel(self):
        line_objs = self.env['shift.management.exchange.shift'].sudo().search([('head_id', '=', self.id)])
        for rec in line_objs:
            rec.unlink()

        self.state = 'cancel'

class ShiftManagementExchangeShift(models.Model):
    _name = "shift.management.exchange.shift"
    _description = 'Shift Exchange/Alter Shift'
    _rec_name = 'date'
    _order = 'date desc'

    head_id = fields.Many2one('shift.management.exchange', ondelete='cascade')

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
                                  domain=[('is_rostering_employee', '=', True)])
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    department_id = fields.Many2one('hr.department', string='Department')
    job_id = fields.Many2one('hr.job', string="Designation")
    manager_id = fields.Many2one('hr.employee', string='Reporting Manager')

    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Hours/Shift',
                                           help="Employee's working schedule.", required=True)
    hour_from_per_day_m = fields.Float(string='Start Time', related="resource_calendar_id.hour_from_per_day_m")
    hour_to_per_day_e = fields.Float(string='End Time', related="resource_calendar_id.hour_to_per_day_e")
    is_over_ride_day = fields.Boolean(string="Over-Ride Day/Night Shift",
                                      related="resource_calendar_id.is_over_ride_day")

    type = fields.Selection([
        ('exchange', 'Exchange'),
        ('alter', 'Alter'),
    ], string='Type', readonly=True, copy=False, index=True, default='exchange')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approved'),
        ('cancel', 'Cancel'),
    ], string='Status', readonly=True, copy=False, index=True, default='draft')

    request_date = fields.Datetime(string='Requested Date', related='head_id.request_date')
    accept_date = fields.Datetime(string='Accepted Date', related='head_id.accept_date')
    approve_date = fields.Datetime(string='Approved Date', related='head_id.approve_date')
    requested_by_id = fields.Many2one('hr.employee', string='Requested By', related='head_id.requested_by_id')
    accepted_by_id = fields.Many2one('hr.employee', string='Accepted By', related='head_id.accepted_by_id')
    approved_by_id = fields.Many2one('hr.employee', string='Approved By', related='head_id.approved_by_id')

    @api.constrains('employee_id', 'date')
    def _check_unique_date_employee_id(self):
        for rec in self:
            msg = 'Same Date `%s` and Employee `%s`' % (rec.date, rec.employee_id.name)
            envobj = self.env['shift.management.exchange.shift']
            conditionlist = [('date', '=', rec.date), ('employee_id', '=', rec.employee_id.id)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)
