# coding=utf-8
from odoo import fields, models, api


class HrEmployeeTransferHistory(models.Model):
    """ Employee Transfer history model """
    _name = 'hr.employee.transfer.history'
    _description = 'Employee Transfer History'

    # ondelete = 'set null'
    employee_id = fields.Many2one('hr.employee', string='Employee Name', required=True, ondelete='cascade')
    type = fields.Selection([
        ('0', 'Same Company'),
        ('1', 'Other Company')
    ],string="Type", required=True)
    from_company = fields.Char(string="From company", required=True)
    to_company = fields.Char(string="To company")
    from_location = fields.Char(string="From", required=True)
    to_location = fields.Char(string="To")
    effective_date = fields.Date(string="Effective Date", required=True)
    from_department_id = fields.Many2one('hr.department', string='From Department')
    to_department_id = fields.Many2one('hr.department', string='To Department')

    prev_from_date = fields.Date(string="Prev.From Date")
    prev_to_date = fields.Date(string="Prev.To Date")
