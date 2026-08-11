from odoo import models, fields, api
from odoo.addons.helper import validator


class EmployeeTraining(models.Model):
    _name = 'employee.training'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee Training"
    _order = "id desc"
    _rec_name = "training_session_name"

    training_session_name = fields.Char(string="Training Session")
    start_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    expenses = fields.Float(string="Total Expenses")
    expense_bear = fields.Char(string="Expenses Bears")
    reason = fields.Text(string="Reason")
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirm'), ('cancel', 'Cancelled')],
        string='Status', default='draft', tracking=True)
    employee_training_ids = fields.One2many('employee.training.list', 'training_id', string="Trainee Employee",
                                            help='Trainee Employee')

    def action_confirm(self):
        for records in self:
            records.sudo().write({'state': 'confirm'})

    def action_cancel(self):
        for records in self:
            records.sudo().write({'state': 'cancel'})


class EmployeeTrainingList(models.Model):
    _name = 'employee.training.list'
    _description = 'Employee Training List'

    employee_id = fields.Many2one('hr.employee', string="Employee", help='Select corresponding Employee')
    training_id = fields.Many2one('employee.training')

    @api.constrains('employee_id')
    def _check_unique_employee_id(self):
        for rec in self:
            msg = 'Employee "%s"' % rec.employee_id.name
            envObj = self.env['employee.training.list']
            conditionList1 = [('employee_id', '=', rec.employee_id.id), ('training_id', '=', rec.training_id.id)]
            validator.check_duplicate_value(rec, envObj, conditionList1, msg)
