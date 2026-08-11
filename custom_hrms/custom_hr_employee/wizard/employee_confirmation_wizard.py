from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class EmployeeConf(models.TransientModel):
    _name = "employee.confirmation.wizard"
    _description = "Employee Confirmation"

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date', default=fields.Date.context_today)
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_emp_conf_rel', 'emp_conf_id', 'employee_id', string='Employees')

    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('Start date cannot be greater than the end date.'))

    @api.onchange('start_date', 'end_date')
    def _onchange_set_employees(self):
        if self.start_date and self.end_date:
            emp_ids = self.env['hr.employee'].search([('date_of_confirmation', '>=', self.start_date), ('date_of_confirmation', '<=', self.end_date), ('employee_type', '=', 'probation')])

            self.employee_ids = [(6, 0, emp_ids.ids)]

    def action_confirm(self):
        for rec in self.employee_ids:
            rec.employee_type_id = ''




