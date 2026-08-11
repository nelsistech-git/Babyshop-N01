from odoo import fields, models, api, _

class AttendanceExtraDataCleanWizard(models.TransientModel):
    _name = "attendance.extra.data.clean.wizard"
    _description = "Attendance Clean Date Wizard"

    employee_ids = fields.Many2many('hr.employee', string='Employee')

    def attendance_extra_data_clean(self):
        for rec in self.employee_ids:
            if rec.initial_employment_date:
                before_joining_data = self.env['employee.attendance.sheet.line'].sudo().search(
                    [('employee_id', '=', rec.id),('date', '<', rec.initial_employment_date)])
                if before_joining_data:
                    before_joining_data.sudo().unlink()

            if rec.is_separated:
                separation_date = rec.separation_date
                if separation_date:
                    after_resign_data = self.env['employee.attendance.sheet.line'].sudo().search(
                        [('employee_id', '=', rec.id),('date', '>', separation_date)])
                    if after_resign_data:
                        after_resign_data.sudo().unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }