from odoo import fields, models


class AttendanceReprocessDates(models.Model):
    _name = 'attendance.reprocess.dates'
    _description = 'Attendance Reprocess Dates'
    _order = 'id desc'

    type = fields.Selection([
        ('leave', 'Leave'),
        ('ph', 'Public Holiday')], string='Type')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    date = fields.Date(string='Date')
    process_flag = fields.Integer(string='Process Flag', default=0)
