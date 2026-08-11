from odoo import models, fields, api, exceptions, _
from datetime import timedelta, date
from odoo.exceptions import ValidationError, UserError

class HrPublicHoliday(models.Model):
    _name = "hr.public.holiday"
    _inherit = ['mail.thread']
    _description = "HR Public Holiday"
    HOLIDAY_TYPE = [
        ('emp', 'Employee'),
        ('dep', 'Department'),
        ('workloc', 'Work Location'),
        ('tag', 'Tags')
    ]
    type_select = fields.Selection(HOLIDAY_TYPE, "By", default='emp')
    emp_ids = fields.Many2many(comodel_name="hr.employee",
                               relation="employee_ph_rel",
                               column1="employee_ph_col2",
                               column2="attendance_ph_col2",
                               string="Employees")
    
    dep_ids = fields.Many2many(comodel_name="hr.department",
                               relation="department_att_ph_rel1",
                               column1="ph_department_col2",
                               column2="att_ph_col3", string="Departments",)
    workloc_ids = fields.Many2many(comodel_name="stock.location",
                               relation="workloc_att_ph_rel1",
                               column1="ph_workloc_col2",
                               column2="att_ph_col3", string="Work Locations", domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    cat_ids = fields.Many2many(comodel_name="hr.employee.category",
                               relation="category__phrel",
                               column1="cat_col2", column2="ph_col2",
                               string="Tags")
    
    name = fields.Char(string="Description", required=True)
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)
    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Not Active')], default='inactive',
        tracking=True,
        string='Status', required=True, index=True)
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
                workloc_ids = self.env['stock.location'].sudo().search([('is_work_loc', '=', True), ('state', '=', 'done')])
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

    def action_refresh_emp(self):
        today = fields.Date.today()
        ph_date = self.date_from
        # if today > ph_date:
        #     raise UserError(_('Refresh can be applied before public holiday start date!'))
        # else:
        self.get_employee_ids()


    @api.constrains('date_from', 'date_to')
    def _check_validity_date(self):
        for records in self:
            if records.date_from and records.date_to:
                if records.date_to < records.date_from:
                    raise exceptions.ValidationError(_('To Date cannot be less than From Date'))

    def action_active(self):
        start_date = self.date_from
        end_date = self.date_to

        delta = end_date - start_date

        emp_list = self.emp_ids

        for i in range(delta.days + 1):
            day = start_date + timedelta(days=i)

            exist_data_obj = self.env['hr.public.holiday.details'].sudo().search(
                [('holiday_id', '=', self.id), ('holiday_date', '=', day)],
                limit=1)
            if not exist_data_obj:
                self.env['hr.public.holiday.details'].sudo().create({
                    'holiday_id': self.id,
                    'holiday_date': day,
                    'holiday_no': 1,
                })
            if day <= date.today():
                # employee list loop
                for rec in emp_list:
                    self.env['attendance.reprocess.dates'].sudo().create({
                        'type': 'ph',
                        'employee_id': rec.id,
                        'date': day,
                    })

        self.state = 'active'

    def action_inactive(self):
        start_date = self.date_from
        end_date = self.date_to

        emp_list = self.emp_ids

        delta = end_date - start_date
        
        for i in range(delta.days + 1):
            day = start_date + timedelta(days=i)

            exist_data_obj = self.env['hr.public.holiday.details'].sudo().search(
                [('holiday_id', '=', self.id), ('holiday_date', '=', day)],
                limit=1)
            exist_data_obj.unlink()
            if day <= date.today():
                for rec in emp_list:
                    self.env['attendance.reprocess.dates'].sudo().create({
                        'type': 'ph',
                        'employee_id': rec.id,
                        'date': day,
                    })
        self.state = 'inactive'


class HrPublicHolidayDetails(models.Model):
    _name = "hr.public.holiday.details"
    _description = "HR Public Holiday Details"
    _order = 'holiday_id, holiday_date'

    holiday_id = fields.Many2one('hr.public.holiday', string="Public Holiday", ondelete='cascade')
    holiday_date = fields.Date(string='Holiday Date')
    holiday_no = fields.Float(string='Number of Day(s)')
