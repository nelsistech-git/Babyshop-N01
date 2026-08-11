from odoo import fields, models
from odoo.exceptions import UserError


class ManualAbsenceWizard(models.TransientModel):
    _name = 'hr.manual.absence.wizard'
    _description = 'Manual Absence'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    date = fields.Date(string='Date')
    user_work_location_id = fields.Many2one('stock.location', related='employee_id.user_work_location_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    id_card_no = fields.Char(string="Employee ID", related='employee_id.id_card_no')
    device_user_id = fields.Char(string='Biometric Device ID', related='employee_id.device_user_id')
    note = fields.Text("Note")
    
    def action_submit_absence(self):
        att_obj = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id), ('attendance_date', '=', self.date)], limit=1)
        if att_obj:
            att_obj.active = False
            att_obj.note = self.note
            
            att_obj.policy_process = '0'
            att_obj.pl_sign_in = 0
            att_obj.pl_sign_out = 0
            att_obj.late_in = 0
            att_obj.late_in_abs = 0
            att_obj.diff_time = 0
            att_obj.act_late_in = 0
            att_obj.act_diff_time = 0
            att_obj.overtime = 0
            att_obj.act_overtime = 0 
            
        else:
            raise UserError("No attendance found for '%s'" % self.employee_id.name)
