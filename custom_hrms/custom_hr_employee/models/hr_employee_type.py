from odoo import api, fields, models
from odoo.addons.helper import validator


class HrEmployeeType(models.Model):
    _name = 'hr.employee.type'
    _description = 'HR Employee Type'

    name = fields.Char(string="Employee Type", required=True, trim=True)
    is_probation = fields.Boolean(string="Is Probation?")
    is_permanent = fields.Boolean(string="Is Permanent?")
    is_contractual = fields.Boolean(string="Is Contractual?")
    is_casual = fields.Boolean(string="Is Casual?")
    is_part_time = fields.Boolean(string="Is Part Time?")
    is_deny_pf = fields.Boolean(string="Is Deny PF?")

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        msg = 'Employee Type "%s"' % self.name
        envobj = self.env['hr.employee.type']
        conditionlist = [('name', '=', self.name)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)
