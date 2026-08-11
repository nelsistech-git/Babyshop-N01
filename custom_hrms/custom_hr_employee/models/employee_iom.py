from odoo import models, fields


class EmployeeIOM(models.Model):
    _name = 'employee.iom'
    _description = "Employee IOM"
    _order = "date desc"
    _rec_name = "employee_id"

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date = fields.Date(string='Date', required=True)
    note = fields.Char(string="Note", required=True)
    reason = fields.Text(string="Reason")
    state = fields.Selection(
        [('pending', 'Pending'), ('approved', 'Approved'), ('cancel', 'Cancelled')],
        string='Status', default='pending')

    # mobile app using
    first_approve_reject = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('pending', 'Pending')
    ], string='1st Approval Status', copy=False, default='pending', help="Pending/Approve/Decline")
    first_approve_reject_id = fields.Many2one('hr.employee', string="1st Approver/Rejecter")

    second_approve_reject = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('pending', 'Pending')
    ], string='2nd Approval Status', copy=False, default='pending', help="Pending/Approve/Decline")
    second_approve_reject_id = fields.Many2one('hr.employee', string="2nd Approver/Rejecter")

    def action_approve(self):
        for records in self:
            records.write({'state': 'approved'})

    def action_cancel(self):
        for records in self:
            records.write({'state': 'cancel'})
