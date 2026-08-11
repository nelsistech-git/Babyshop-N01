from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    loan_request = fields.Integer('Loan Request Per Year', default=1, required=True, groups="hr.group_hr_user")
