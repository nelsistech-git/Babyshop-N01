from odoo import fields, models, api
from odoo.addons.helper import validator


class HrEmployeeDisciplinaryType(models.Model):
    """ Employee disciplinary Record Type"""

    _name = 'hr.employee.disciplinary.type'
    _description = 'Employee Disciplinary Type'

    name = fields.Char(string="Name", required=True, trim=True)
    allow_date_range = fields.Boolean(string="Allow Date Range")
    allow_payslip = fields.Boolean(string="Allow Payslip")

    @api.constrains('name')
    def _check_unique_constraint(self):
        """ Check unique name """
        msg = "Name " + self.name
        envobj = self.env['hr.employee.disciplinary.type']
        conditionlist = [('name', '=ilike', self.name)]

        validator.check_duplicate_value(self, envobj, conditionlist, msg)
