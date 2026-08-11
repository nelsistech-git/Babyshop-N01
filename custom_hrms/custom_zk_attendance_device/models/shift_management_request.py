from odoo import models, fields, api
import datetime
from datetime import datetime
from odoo.addons.helper import validator
from odoo.exceptions import UserError, ValidationError

class ShiftManagementRequest(models.Model):
    _name = "shift.management.request"
    _description = "Shift Management Request"
    _rec_name = 'employee_id'

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

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, default=_default_employee, domain=lambda self: self._set_domain_employee())

    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    department_id = fields.Many2one('hr.department', string='Department')
    job_id = fields.Many2one('hr.job', string="Designation")
    manager_id = fields.Many2one('hr.employee', string='Reporting Manager')

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Hours/Shift', help="Employee's working schedule.", required=True)
    hour_from_per_day_m = fields.Float(string='Start Time', related="resource_calendar_id.hour_from_per_day_m")
    hour_to_per_day_e = fields.Float(string='End Time', related="resource_calendar_id.hour_to_per_day_e")
    is_over_ride_day = fields.Boolean(string="Over-Ride Day/Night Shift", related="resource_calendar_id.is_over_ride_day")
    short_name = fields.Char(string='Shift Name', help='Shift Example: A or B or C etc',
                             related='resource_calendar_id.short_name')

    request_date = fields.Datetime(string='Requested Date')
    approve_date = fields.Datetime(string='Approved Date')
    cancel_date = fields.Datetime(string='Cancelled Date')
    requested_by_id = fields.Many2one('hr.employee', string='Requested By')
    approved_by_id = fields.Many2one('hr.employee', string='Approved By')
    cancelled_by_id = fields.Many2one('hr.employee', string='Cancelled By')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Requested'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, default='draft')
    
    @api.constrains('employee_id', 'date_from', 'date_to')
    def _check_unique_date_range(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise ValidationError('Start Date can not be greater than End Date for `%s`!' % (rec.employee_id.name))
            else:
                msg = 'Same request of the employee "%s"' % (rec.employee_id.name)
                envobj = self.env['shift.management.request']
                conditionlist = [('employee_id', '=', rec.employee_id.id), ('date_from', '=', rec.date_from), ('date_to', '=', rec.date_to)]
                validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.user_work_location_id = self.employee_id.user_work_location_id.id or False

            self.job_id = self.employee_id and self.employee_id.job_id and \
                          self.employee_id.job_id.id or False
            self.department_id = self.employee_id and self.employee_id.department_id and \
                                 self.employee_id.department_id.id or False

            manager_id = None
            if self.department_id:
                if self.department_id.manager_id:
                    manager_id = self.department_id.manager_id.id
            if not manager_id:
                if self.employee_id.parent_id:
                    manager_id = self.employee_id.parent_id.id

            self.manager_id = manager_id

    def action_draft(self):
        self.state = 'draft'

    def action_confirm(self):
        current_datetime = fields.Datetime.now()
        for rec in self:
            rec.state = 'confirm'
            rec.request_date = current_datetime

            employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            rec.requested_by_id = employee_id and employee_id.id or False

    def action_confirm_all(self):
        current_datetime = fields.Datetime.now()

        rows = self.env['shift.management.request'].sudo().search([('state', '=', 'draft')])
        for rec in rows:
            rec.state = 'confirm'
            rec.request_date = current_datetime

            employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            rec.requested_by_id = employee_id and employee_id.id or False

    def action_approve(self):
        current_datetime = fields.Datetime.now()
        for rec in self:
            rec.state = 'approve'
            rec.approve_date = current_datetime

            employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            rec.approved_by_id = employee_id and employee_id.id or False

            # if rec.code == 'New':
            #     rec.code = self.env['ir.sequence'].get('stock_unrealized_profit_loss_code')
    def action_approve_all(self):
        current_datetime = fields.Datetime.now()
        rows = self.env['shift.management.request'].sudo().search([('state', '=', 'confirm')])

        for rec in rows:
            rec.state = 'approve'
            rec.approve_date = current_datetime
            employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            rec.approved_by_id = employee_id and employee_id.id or False

    def action_cancel(self):
        employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
        cancelled_by_id = employee_id and employee_id.id or False
        current_datetime = fields.Datetime.now()

        self.state = 'cancel'
        self.cancel_date = current_datetime,
        self.cancelled_by_id = cancelled_by_id

