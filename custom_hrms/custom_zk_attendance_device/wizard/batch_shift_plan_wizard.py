import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import datetime
from datetime import timedelta


class BatchShiftPlanWizard(models.TransientModel):
    _name = 'batch.shift.plan.wizard'
    _description = 'Batch Shift Plan'

    TYPE_VAL = [
        ('emp', 'Employee'),
        ('dep', 'Department'),
        ('workloc', 'Work Location'),
        ('tag', 'Tags')
    ]
    type_select = fields.Selection(TYPE_VAL, "By", default='emp')


    dep_ids = fields.Many2many("hr.department", string="Departments")
    workloc_ids = fields.Many2many("stock.location", string="Work Locations", domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    cat_ids = fields.Many2many("hr.employee.category", string="Tags")
    emp_ids = fields.Many2many('hr.employee', string="Employees")

    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)
    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Hours/Shift', help="Employee's working schedule.", required=True)
    short_name = fields.Char(string='Shift Short Name', help='Shift Example: A or B or C etc', related='resource_calendar_id.short_name')

    note = fields.Text("Notes")
    set_dept = fields.Boolean(string='All Set')

    @api.onchange('type_select', 'set_dept')
    def _onchange_set_dept(self):
        if self.type_select == 'dep':
            if self.set_dept:
                dept_ids = self.env['hr.department'].sudo().search([])
                return {'value': {'dep_ids': dept_ids.ids, 'workloc_ids': None, 'cat_ids': None}}
            else:
                return {'value': {'dep_ids': None, 'workloc_ids': None, 'cat_ids': None, 'emp_ids': None}}
        elif self.type_select == 'workloc':
            if self.set_dept:
                workloc_ids = self.env['stock.location'].sudo().search(
                    [('is_work_loc', '=', True), ('state', '=', 'done')])
                return {'value': {'workloc_ids': workloc_ids.ids, 'dep_ids': None, 'cat_ids': None}}
            else:
                return {'value': {'dep_ids': None, 'workloc_ids': None, 'cat_ids': None, 'emp_ids': None}}
        elif self.type_select == 'tag':
            if self.set_dept:
                cat_ids = self.env['hr.employee.category'].sudo().search([])
                return {'value': {'workloc_ids': None, 'dep_ids': None, 'cat_ids': cat_ids.ids}}
            else:
                return {'value': {'dep_ids': None, 'workloc_ids': None, 'cat_ids': None, 'emp_ids': None}}
        else:
            return {'value': {'emp_ids': None, 'dep_ids': None, 'workloc_ids': None, 'cat_ids': None}}

    @api.onchange("dep_ids", "cat_ids", "workloc_ids")
    def get_employee_ids(self):
        emp_ids = []
        if self.type_select == 'dep':
            self.emp_ids = self.env['hr.employee'].sudo().search(
                [('department_id.id', 'in', self.dep_ids.ids), ('initial_employment_date', '<=', self.date_to)])
        elif self.type_select == 'tag':
            for employee in self.env['hr.employee'].sudo().search([('initial_employment_date', '<=', self.date_to)]):
                list1 = self.cat_ids.ids
                list2 = employee.category_ids.ids
                match = any(map(lambda v: v in list1, list2))
                if match:
                    emp_ids.append(employee.id)
            self.emp_ids = self.env['hr.employee'].sudo().search(
                [('id', 'in', emp_ids)])
        elif self.type_select == 'workloc':
            self.emp_ids = self.env['hr.employee'].sudo().search(
                [('user_work_location_id', 'in', self.workloc_ids.ids), ('initial_employment_date', '<=', self.date_to)])


    @api.constrains('date_from', 'date_to')
    def _check_validity_date(self):
        for records in self:
            if records.date_from and records.date_to:
                if records.date_to < records.date_from:
                    raise ValidationError(_('To Date cannot be less than From Date'))


    def action_submit_shift_plan(self):
        date_from = self.date_from
        date_to = self.date_to
        current_datetime = fields.Datetime.now()

        employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
        requested_by_id = employee_id and employee_id.id or False

        emp_list = self.emp_ids
        shift_obj = self.env['shift.management.request'].sudo()
        for employee in emp_list:
            exist_data_obj = shift_obj.search([('employee_id.id', '=', employee.id), ('date_from', '=', date_from), ('date_to', '=', date_to)], limit=1)
            if exist_data_obj:
                exist_data_obj.write({
                    'user_work_location_id': employee.user_work_location_id.id or False,
                    'job_id': employee.job_id.id or False,
                    'department_id': employee.department_id.id or False,
                    'manager_id': employee.department_id.manager_id.id or employee.parent_id.id or False,

                    'resource_calendar_id': self.resource_calendar_id.id,
                    'request_date': current_datetime,
                    'requested_by_id': requested_by_id,
                    'approve_date': current_datetime,
                    'approved_by_id': requested_by_id,
                    'state': 'approve'
                })
            else:
                shift_obj.create({
                    'employee_id': employee.id,
                    'user_work_location_id': employee.user_work_location_id.id or False,
                    'job_id': employee.job_id.id or False,
                    'department_id': employee.department_id.id or False,
                    'manager_id': employee.department_id.manager_id.id or employee.parent_id.id or False,
                    'date_from': date_from,
                    'date_to': date_to,
                    'resource_calendar_id': self.resource_calendar_id.id,
                    'request_date': current_datetime,
                    'requested_by_id': requested_by_id,
                    'approve_date': current_datetime,
                    'approved_by_id': requested_by_id,
                    'state': 'approve'

                })

    def action_cancel_shift_plan(self):
        date_from = self.date_from
        date_to = self.date_to
        current_datetime = fields.Datetime.now()

        employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
        cancelled_by_id = employee_id and employee_id.id or False

        emp_list = self.emp_ids
        shift_obj = self.env['shift.management.request'].sudo()
        for employee in emp_list:
            exist_data_rows = shift_obj.search([('employee_id.id', '=', employee.id), ('date_from', '=', date_from), ('date_to', '=', date_to), ('resource_calendar_id', '=', self.resource_calendar_id.id),('state', '!=', 'cancel')])
            for rec in exist_data_rows:
                rec.write({
                    'state': 'cancel',
                    'cancel_date': current_datetime,
                    'cancelled_by_id': cancelled_by_id
                })


