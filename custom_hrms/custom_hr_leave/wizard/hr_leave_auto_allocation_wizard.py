from odoo import fields, models


class HrLeaveAutoAllocationWizard(models.TransientModel):
    _name = "hr.leave.auto.allocation.wizard"
    _description = "HR Leave Auto Allocation"

    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  domain=[('employee_type_id.is_permanent', '=', True)])

    def button_hr_leave_auto_allocation(self):
        employee_id = self.employee_id
        emp_obj = self.env['hr.employee']
        if employee_id:
            emp_obj.auto_leave_allocation(employee_id=employee_id.id, yearly_allocation=True)
        else:
            emp_obj.auto_leave_allocation(yearly_allocation=True)
