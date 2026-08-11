from odoo import exceptions, fields, models, _
from datetime import datetime, date

class EmployeeRejoiningWizard(models.TransientModel):
    _name = "employee.rejoining.wizard"
    _description = "Employee Rejoining"

    employee_id = fields.Many2one('hr.employee', string='Employee', domain=[('active', '=', False), ('is_separated', '=', True), ('user_id', '!=', False)])
    employee_type_id = fields.Many2one('hr.employee.type', string='Employee Type')
    initial_employment_date = fields.Date(string='Date of Joining', default=datetime.now().date())

    def action_employee_rejoining(self):
        contact_no = self.employee_id.contact_no
        #self.employee_id.contact_no = ''
        work_email = self.employee_id.work_email
        #self.employee_id.work_email = ''
        self.employee_id.user_id = None
        #self.employee_id.device_user_id = ''

        #----------------
        emp_obj = self.employee_id.copy()
        name = self.employee_id.name
        emp_obj.name = name
        emp_obj.contact_no = contact_no
        emp_obj.work_email = ''
        emp_obj.employee_type_id = self.employee_type_id
        emp_obj.initial_employment_date = self.initial_employment_date
        emp_obj.address_home_id = None
        emp_obj.id_card_no = ''
        emp_obj.device_user_id = ''

        emp_obj.active = True
        emp_obj.is_separated = False
        emp_obj.resigned = False
        emp_obj.fired = False
        emp_obj.separation_date = None
        emp_obj.pf_settlement_status = False
        emp_obj.final_settlement_status = False

        #-----------
        action_ctx = dict(self.env.context)
        view_id = self.env.ref('hr.view_employee_form').id
        action_vals = {
            'name': _('Employees'),
            'res_model': 'hr.employee',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': emp_obj.id,
            'context': action_ctx,
            'type': 'ir.actions.act_window',
        }
        return action_vals
